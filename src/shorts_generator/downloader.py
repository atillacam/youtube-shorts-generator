"""Pixabay Video API downloader with orientation scoring and diversity randomization."""

import os
import re
import random
import urllib.request
import requests
from typing import Optional

from .config import PIXABAY_API_KEY


def is_valid_video_file(file_path: str, min_size_bytes: int = 1000) -> bool:
    """Checks whether a downloaded video file exists, exceeds minimum size, and has readable bytes."""
    if not os.path.exists(file_path):
        return False
    if os.path.getsize(file_path) < min_size_bytes:
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(32)
            return len(header) >= 16
    except Exception:
        return False


def score_video_hit(hit_item: dict) -> int:
    """Calculates suitability score favoring vertical 9:16 portrait orientation and HD resolutions."""
    videos = hit_item.get("videos", {})
    info = videos.get("large") or videos.get("medium") or videos.get("small") or {}
    w = info.get("width", 0)
    h = info.get("height", 0)

    is_vertical = 15 if h > w else 0
    is_hd = 8 if (w >= 1080 or h >= 1080) else (4 if (w >= 720 or h >= 720) else 0)
    return is_vertical + is_hd



def select_best_stream_info(videos: dict) -> Optional[dict]:
    """Selects best candidate stream under maximum file size thresholds."""
    for q_name in ["large", "medium", "small"]:
        candidate = videos.get(q_name)
        if candidate and candidate.get("url"):
            if q_name == "medium" and (candidate.get("width", 0) >= 720 or candidate.get("height", 0) >= 720):
                return candidate
            if q_name == "large":
                if candidate.get("size", 0) > 35 * 1024 * 1024 and videos.get("medium"):
                    return videos.get("medium")
                return candidate
    return videos.get("large") or videos.get("medium") or videos.get("small")


def download_scene_background_videos(
    scene_queries: list[str],
    output_dir: str = "backgrounds",
    count: int = 3,
) -> list[str]:
    """Downloads portrait HD background videos matching each scene (Hook, Body, CTA) from Pixabay.

    Tracks downloaded video IDs across iterations to avoid repeating duplicate footage.
    """
    os.makedirs(output_dir, exist_ok=True)
    api_key = PIXABAY_API_KEY
    if not api_key:
        print("[Pixabay] Uyarı: PIXABAY_API_KEY ortam değişkeni bulunamadı (.env dosyasını kontrol edin).")
        return []

    scene_labels = ["hook", "body", "cta"]
    downloaded_files = []
    used_video_ids = set()
    api_url = "https://pixabay.com/api/videos/"

    print(f"\n[Pixabay] Sahne bazlı arka plan videoları aranıyor ({len(scene_queries)} sahne)...")

    for i in range(count):
        raw_query = scene_queries[i] if i < len(scene_queries) else scene_queries[-1]
        scene_label = scene_labels[i] if i < len(scene_labels) else f"scene_{i+1}"
        clean_query = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_query).strip()

        words = clean_query.split()
        search_candidates = [clean_query]
        if len(words) >= 3:
            search_candidates.append(" ".join(words[:2]))
        if len(words) >= 2:
            search_candidates.append(words[0])
        search_candidates.extend(["technology dark", "cinematic abstract", "dark atmosphere"])

        hits = []
        successful_query = ""
        for q_attempt in search_candidates:
            if not q_attempt.strip():
                continue
            try:
                params = {
                    "key": api_key,
                    "q": q_attempt,
                    "video_type": "film",
                    "per_page": 20,
                    "safesearch": "true",
                }
                resp = requests.get(api_url, params=params, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    candidate_hits = [h for h in data.get("hits", []) if h.get("id") not in used_video_ids]
                    if candidate_hits:
                        hits = candidate_hits
                        successful_query = q_attempt
                        break
            except Exception as req_err:
                print(f"[Pixabay] '{q_attempt}' sorgu hatası: {req_err}")
                continue

        if not hits:
            print(f"[Pixabay] Sahne {i+1} ({scene_label.upper()}) için uygun video bulunamadı.")
            continue

        sorted_hits = sorted(hits, key=score_video_hit, reverse=True)
        pool_size = min(5, len(sorted_hits))
        top_pool = sorted_hits[:pool_size]
        chosen_hit = random.choice(top_pool)
        used_video_ids.add(chosen_hit.get("id"))

        info = select_best_stream_info(chosen_hit.get("videos", {}))
        if not info or not info.get("url"):
            continue

        video_url = info["url"]
        output_file = os.path.join(output_dir, f"scene_{i+1}_{scene_label}.mp4")

        try:
            w_curr = info.get("width", 0)
            h_curr = info.get("height", 0)
            orientation = "Dikey (Portrait)" if h_curr > w_curr else "Yatay (Landscape)"
            print(f"[Pixabay] Sahne {i+1}/{count} [{scene_label.upper()} - '{successful_query}'] indiriliyor ({w_curr}x{h_curr} - {orientation})...")

            downloaded = False
            try:
                r = requests.get(video_url, stream=True, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    with open(output_file, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                    downloaded = True
            except Exception:
                downloaded = False

            if not downloaded:
                req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req) as resp, open(output_file, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                downloaded = True

            if downloaded and is_valid_video_file(output_file, min_size_bytes=1000):
                size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"[Pixabay] Başarılı! {output_file} kaydedildi ({size_mb:.2f} MB)")
                downloaded_files.append(output_file)
            else:
                print(f"[Pixabay] Video indirilemedi veya dosya bozuk: {output_file}")

        except Exception as dl_err:
            print(f"[Pixabay] Sahne {i+1} indirme hatası: {dl_err}")

    print(f"[Pixabay] Toplam {len(downloaded_files)}/{count} sahne videosu başarıyla hazırlandı.")
    return downloaded_files


def download_background_video(
    query: str,
    count: int = 3,
    output_prefix: str = "bg",
) -> list[str]:
    """Backward compatibility wrapper for downloading background clips."""
    return download_scene_background_videos([query] * count, output_dir=".", count=count)
