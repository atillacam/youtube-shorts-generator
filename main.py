import os
import sys
import re
import textwrap
import asyncio
import urllib.request
import urllib.parse
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import edge_tts

# MoviePy importu (MoviePy 1.x ve 2.x sürümleriyle tam uyumlu)
try:
    from moviepy.editor import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        ColorClip,
        TextClip,
        CompositeVideoClip,
        CompositeAudioClip,
        concatenate_videoclips,
        vfx,
        afx,
    )
    try:
        from moviepy.audio.fx.all import volumex, audio_loop
    except ImportError:
        volumex = None
        audio_loop = None
except ImportError:
    from moviepy import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        ColorClip,
        TextClip,
        CompositeVideoClip,
        CompositeAudioClip,
        concatenate_videoclips,
        vfx,
        afx,
    )
    volumex = None
    audio_loop = None


def apply_audio_volume(clip, factor: float):
    """MoviePy 1.x (volumex) ve 2.x (with_volume_scaled / MultiplyVolume) uyumlu ses seviyesi çarpanı."""
    if volumex is not None:
        try:
            return volumex(clip, factor)
        except Exception:
            pass
    if hasattr(clip, "with_volume_scaled"):
        return clip.with_volume_scaled(factor)
    elif hasattr(clip, "with_effects") and hasattr(afx, "MultiplyVolume"):
        return clip.with_effects([afx.MultiplyVolume(factor)])
    elif hasattr(clip, "volumex"):
        return clip.volumex(factor)
    return clip


def apply_audio_loop(clip, target_duration: float):
    """MoviePy 1.x (audio_loop) ve 2.x (AudioLoop) uyumlu ses döngüsü."""
    if audio_loop is not None:
        try:
            return audio_loop(clip, duration=target_duration)
        except Exception:
            pass
    if hasattr(clip, "with_effects") and hasattr(afx, "AudioLoop"):
        return clip.with_effects([afx.AudioLoop(duration=target_duration)])
    else:
        from moviepy import concatenate_audioclips
        n_loops = int(target_duration // clip.duration) + 1
        looped = concatenate_audioclips([clip] * n_loops)
        if hasattr(looped, "subclipped"):
            return looped.subclipped(0, target_duration)
        else:
            return looped.subclip(0, target_duration)

# Windows konsolunda UTF-8 karakterlerin düzgün görüntülenmesi için
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

# Gemini API anahtarını al ve yapılandır
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def generate_shorts_script(topic: str) -> str:
    """Verilen bir konu başlığından 30 saniyelik, viral potansiyeli yüksek
    bir YouTube Shorts senaryosu üretir.
    """
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY ortam değişkeni bulunamadı. Lütfen .env dosyasını doldurun."
        )

    prompt = f"""
You are an elite viral content creator specializing in hyper-retention YouTube Shorts and TikToks.

Write the script entirely in English, keeping the tone aggressive, urgent, and mysterious. Do not include any Turkish words.

Topic: {topic}

Write the script using ultra-short, punchy sentences. Eliminate all filler words. Every single sentence must trigger curiosity. Keep the total spoken text around 60-75 words for a highly energetic, fast-paced 30-second delivery.

The script MUST follow this exact 3-part structure:
1. [0-3s] Hook: An electrifying, scroll-stopping statement or shocking question that violently grabs attention within the first 2 seconds. Make it bold, provocative, or alarming to shock the viewer.
2. [3-25s] Body: 2-3 rapid-fire, jaw-dropping facts delivered with extreme momentum and zero fluff. Every word must hit hard.
3. [25-30s] Call to Action (CTA): A sharp, psychological cliffhanger or controversial question demanding viewers to comment and subscribe before it is too late.

For each section, you MUST strictly use this exact format:
- Visual: [Brief description of fast-paced visual scene or footage]
- Voiceover: [The exact words spoken by the narrator]

CRITICAL RULES:
- Write exclusively in English.
- Voiceover lines must contain ONLY spoken dialogue. Never include bracketed directions, emojis, asterisks, or sound effect markers inside Voiceover lines.
- Keep sentences short (3-8 words per sentence). Speak with intensity and pace.
- At the very end of your response, on a new line, add exactly:
SEARCH_QUERY: [A single English word representing the core visual theme to find matching background footage. You MUST choose a cinematic, atmospheric, or moody word that fits the topic (e.g., dark, horror, mystery, space, cyber, ancient, thriller, gold).]
"""

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite"]
    last_error = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Senaryo üretilemedi: {last_error}")


def extract_search_query(script: str, default: str = "dark") -> str:
    """Senaryonun altındaki SEARCH_QUERY etiketinden arka plan arama terimini ayıklar."""
    match = re.search(r"SEARCH_QUERY\s*:\s*\[?([a-zA-Z0-9_\-]+)\]?", script, re.IGNORECASE)
    if match:
        query = match.group(1).strip().lower()
        if query:
            return query
    return default


def download_background_video(
    query: str,
    count: int = 3,
    output_prefix: str = "bg",
) -> list[str]:
    """Pixabay Video API kullanarak arama sorgusuna uygun en fazla `count` adet
    (varsayılan: 3) kaliteli arka plan videosu bulur ve ('bg_1.mp4', 'bg_2.mp4', 'bg_3.mp4')
    olarak indirir.

    Args:
        query: İngilizce arama terimi (örn. 'dark', 'mystery', 'horror', 'space').
        count: İndirilecek video sayısı (varsayılan: 3).
        output_prefix: Dosya adı öneki (varsayılan: 'bg').

    Returns:
        list[str]: Başarıyla indirilen video dosyalarının yolları listesi.
    """
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        print("[Pixabay] Uyarı: PIXABAY_API_KEY ortam değişkeni bulunamadı (.env dosyasını kontrol edin).")
        return []

    clean_query = query.strip().replace("[", "").replace("]", "")
    print(f"\n[Pixabay] '{clean_query}' araması için {count} adet arka plan videosu sorgulanıyor...")

    api_url = "https://pixabay.com/api/videos/"
    params = {
        "key": api_key,
        "q": clean_query,
        "video_type": "film",
        "per_page": 20,
        "safesearch": "true",
    }

    try:
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits", [])

        # Eğer sorgu ile sonuç bulunamadıysa atmosferik 'dark' sorgusu ile dene
        if not hits:
            print(f"[Pixabay] '{clean_query}' için video bulunamadı. Genel atmosferik 'dark' sorgusu deneniyor...")
            params["q"] = "dark"
            response = requests.get(api_url, params=params, timeout=15)
            data = response.json()
            hits = data.get("hits", [])

        if not hits:
            print("[Pixabay] Uyarı: Hiçbir arka plan videosu bulunamadı.")
            return []

        downloaded_files = []

        # Dikey (portrait: height > width) ve HD formatta olan videoları önceliklendir
        def score_hit(h_item):
            v_dict = h_item.get("videos", {})
            v_info = v_dict.get("large") or v_dict.get("medium") or v_dict.get("small") or {}
            w = v_info.get("width", 0)
            h = v_info.get("height", 0)
            # Dikey video (9:16 portrait) en yüksek önceliğe sahiptir
            is_vertical = 10 if h > w else 0
            # HD çözünürlük puanı
            is_hd = 5 if (w >= 1080 or h >= 1080) else (2 if (w >= 720 or h >= 720) else 0)
            return is_vertical + is_hd

        sorted_hits = sorted(hits, key=score_hit, reverse=True)

        # Aday videoları sırayla dene ve count adet indir
        for idx, hit in enumerate(sorted_hits):
            if len(downloaded_files) >= count:
                break

            videos = hit.get("videos", {})
            # En uygun HD/kaliteli varyantı seç (aşırı büyük 4K dosyaları yerine optimize HD tercih et)
            info = None
            for q_name in ["large", "medium", "small"]:
                candidate = videos.get(q_name)
                if candidate and candidate.get("url"):
                    if q_name == "medium" and (candidate.get("width", 0) >= 720 or candidate.get("height", 0) >= 720):
                        info = candidate
                        break
                    if q_name == "large":
                        if candidate.get("size", 0) > 35 * 1024 * 1024 and videos.get("medium"):
                            info = videos.get("medium")
                        else:
                            info = candidate
                        break
            if not info or not info.get("url"):
                info = videos.get("large") or videos.get("medium") or videos.get("small")

            if not info or not info.get("url"):
                continue

            video_url = info["url"]
            output_file = f"{output_prefix}_{len(downloaded_files) + 1}.mp4"

            try:
                w_curr = info.get("width", 0)
                h_curr = info.get("height", 0)
                orientation = "Dikey (Portrait)" if h_curr > w_curr else "Yatay (Landscape)"
                print(f"[Pixabay] Video {len(downloaded_files) + 1}/{count} indiriliyor ({w_curr}x{h_curr} - {orientation})...")
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

                if downloaded and os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    size_mb = os.path.getsize(output_file) / (1024 * 1024)
                    print(f"[Pixabay] Başarılı! {output_file} kaydedildi ({size_mb:.2f} MB)")
                    downloaded_files.append(output_file)
                else:
                    print(f"[Pixabay] Video indirilemedi: {output_file}")
            except Exception as dl_err:
                print(f"[Pixabay] Video {len(downloaded_files) + 1} indirme hatası: {dl_err}. Sıradaki video deneniyor...")

        print(f"[Pixabay] Toplam {len(downloaded_files)}/{count} arka plan videosu hazırlandı.")
        return downloaded_files

    except Exception as e:
        print(f"[Pixabay] Pixabay API sorgulama hatası: {e}")
        return []


def extract_voiceover(script: str) -> str:
    """Üretilen senaryo metninden yalnızca seslendirilecek kısımları (Voiceover) ayıklar.

    'Visual:', 'Hook:', 'CTA:', 'SEARCH_QUERY:', 'IMAGE_PROMPT:', 'Görsel:' gibi yönlendirmeleri, sahne açıklamalarını
    ve zaman damgalarını sese dahil etmemek için temizler.
    """
    # 1. Aşama: 'Voiceover:' veya 'Seslendirme:' etiketli blokları yakala
    prefix = r"(?:^|\n)\s*(?:[-*•#\d\.\(\)]+\s*)?(?:\*\*|\*)?(?:Voiceover|Voice-over|Narration|Voice|Seslendirme|Dış\s*Ses|Ses|Metin)(?:\*\*|\*)?\s*:\s*"
    delimiter = r"(?=(?:\n\s*(?:[-*•#\d\.\(\)]+\s*)?(?:\*\*|\*)?(?:Visual|Visuals|Scene|Video|Voiceover|Voice-over|Narration|Voice|Hook|Body|CTA|Call\s*to\s*Action|SEARCH_QUERY|IMAGE_PROMPT|Image_Prompt|Image|Görsel|Seslendirme|Dış\s*Ses|Kanca|Gövde|Kapanış|Sahne|\d+[\.\)])|\Z))"
    pattern = prefix + r"(.*?)" + delimiter

    matches = re.findall(pattern, script, flags=re.IGNORECASE | re.DOTALL)

    voiceover_parts = []
    for m in matches:
        cleaned = m.strip()
        if cleaned:
            voiceover_parts.append(cleaned)

    # 2. Aşama: Eğer özel etiketler bulunamadıysa satır bazlı filtreleme fallback'i uygula
    if not voiceover_parts:
        lines = script.splitlines()
        ignore_prefixes = (
            "visual", "visuals", "scene", "video", "footage", "b-roll",
            "hook", "body", "cta", "call to action", "note:", "title:",
            "search_query", "image_prompt", "image prompt", "image:", "image",
            "görsel", "kanca", "gövde", "kapanış", "sahne", "ekran", "not:"
        )
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^\[?\d+[-–]\d+\s*s[en]*\]?", stripped, re.IGNORECASE):
                continue

            cleaned_prefix = re.sub(r"^[\*\-\d\.\s\[\]]+", "", stripped).lower()
            if any(cleaned_prefix.startswith(tag) for tag in ignore_prefixes):
                continue

            match_vo = re.match(r"^[\*\-\s]*(?:Voiceover|Voice-over|Narration|Voice|Seslendirme|Dış\s*Ses|Ses|Metin)\s*:\s*(.*)", stripped, re.IGNORECASE)
            if match_vo:
                voiceover_parts.append(match_vo.group(1).strip())
            else:
                voiceover_parts.append(stripped)

    full_text = " ".join(voiceover_parts)

    # Parantez içi veya köşeli parantez içi sahne yönlendirmelerini temizle
    full_text = re.sub(r"[\(\[][^\)\]]*(?:camera|visual|zoom|effect|sfx|music|sound effect|smile|cut|scene|b-roll|footage|kamera|görsel|zoom|efekt|müzik|ses efekti|gülümse|kesme|sahne)[^\)\]]*[\)\]]", "", full_text, flags=re.IGNORECASE)
    # Kalan markdown işaretlerini (*, _, #, `) ve gereksiz boşlukları temizle
    full_text = re.sub(r"[\*_#`]", "", full_text)
    full_text = re.sub(r"\s+", " ", full_text).strip()

    return full_text


def srt_to_vtt(srt_content: str) -> str:
    """SRT biçimindeki altyazı içeriğini standart WebVTT formatına dönüştürür."""
    vtt_lines = ["WEBVTT\n"]
    for line in srt_content.strip().splitlines():
        if "-->" in line:
            vtt_lines.append(line.replace(",", "."))
        else:
            vtt_lines.append(line)
    return "\n".join(vtt_lines) + "\n"


async def text_to_speech(
    text: str, 
    output_audio: str = "output.mp3", 
    output_subtitle: str = "output.srt",
    voice: str = "en-US-ChristopherNeural",
) -> tuple[str, str]:
    """Verilen metni Edge TTS kullanarak yüksek kaliteli bir ses dosyasına (mp3)
    ve SubMaker modülüyle sesle birebir zaman uyumlu altyazı dosyalarına (.srt ve .vtt) dönüştürür.
    
    Args:
        text: Seslendirilecek metin.
        output_audio: Ses dosyası çıktı yolu (varsayılan: output.mp3).
        output_subtitle: Altyazı dosyası çıktı yolu (varsayılan: output.srt).
        voice: Kullanılacak ses modeli (varsayılan: en-US-ChristopherNeural, alternatif: en-GB-RyanNeural).
        
    Returns:
        tuple[str, str]: (output_audio, output_subtitle) yolları.
    """
    if not text.strip():
        raise ValueError("Seslendirilecek metin bulunamadı!")

    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()

    with open(output_audio, "wb") as f_audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f_audio.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

    srt_content = submaker.get_srt()
    with open(output_subtitle, "w", encoding="utf-8") as f_sub:
        f_sub.write(srt_content)

    # İstenen .vtt formatını da aynı içerikle kaydet
    vtt_path = os.path.splitext(output_subtitle)[0] + ".vtt"
    with open(vtt_path, "w", encoding="utf-8") as f_vtt:
        f_vtt.write(srt_to_vtt(srt_content))

    return output_audio, output_subtitle


def parse_subtitles(file_path: str) -> list[tuple[float, float, str]]:
    """SRT veya VTT dosyasını ayrıştırarak (başlangıç_sn, bitiş_sn, metin) listesi döndürür."""
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    subtitles = []

    for block in blocks:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        time_match = None
        text_lines = []
        for line in lines:
            m = re.match(
                r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
                line,
            )
            if m:
                time_match = m
            elif time_match:
                text_lines.append(line)

        if time_match and text_lines:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = [int(x) for x in time_match.groups()]
            start_sec = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
            end_sec = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
            text = " ".join(text_lines).strip()
            if text and end_sec > start_sec:
                subtitles.append((start_sec, end_sec, text))

    return subtitles


def split_cue_into_shorts_chunks(
    start: float, end: float, text: str, max_words: int = 2
) -> list[tuple[float, float, str]]:
    """Metni TikTok / YouTube Shorts stiline uygun olarak SADECE 1 veya maksimum 2 kelimelik
    çok kısa ve dinamik parçalara böler, süreleri kelime uzunluklarına göre hassas dağıtır.
    """
    words = text.split()
    if not words:
        return []

    # Eğer zaten 1 veya 2 kelimeden oluşuyorsa doğrudan döndür
    if len(words) <= max_words:
        return [(start, end, text.strip())]

    # Kelimeleri SADECE 1 veya maksimum 2 kelimelik parçalara ayır
    # Noktalama işaretlerine ve konuşma duraklamalarına saygı göster
    chunks = []
    i = 0
    while i < len(words):
        w1 = words[i]
        if i + 1 >= len(words):
            chunks.append([w1])
            i += 1
        else:
            w2 = words[i + 1]
            # w1 noktalama işaretiyle bitiyorsa (virgül, nokta vb.), duraklama için tek kelime yap
            if any(w1.endswith(p) for p in [".", ",", "!", "?", ":", ";", "—", "-"]):
                chunks.append([w1])
                i += 1
            else:
                chunks.append([w1, w2])
                i += 2

    # Her parçanın karakter uzunluğuna göre süreyi orantısal olarak dağıt
    total_chars = sum(len(w) for w in words)
    duration = end - start

    sub_cues = []
    cur_start = start
    for idx, chk in enumerate(chunks):
        chk_text = " ".join(chk).strip()
        chk_chars = sum(len(w) for w in chk)
        if idx == len(chunks) - 1:
            chk_end = end
        else:
            chk_duration = duration * (chk_chars / total_chars)
            chk_end = cur_start + chk_duration

        if chk_end > cur_start:
            sub_cues.append((cur_start, chk_end, chk_text))
        cur_start = chk_end

    return sub_cues



def create_subtitle_clips(
    subtitles: list[tuple[float, float, str]],
    font_size: int = 96,
) -> list[CompositeVideoClip]:
    """Zaman damgalı altyazı listesini TikTok / YouTube Shorts dinamiklerine uygun olarak
    SADECE 1 veya maksimum 2 kelimelik, tek satırda ortalanmış, agresif ve kalın (Impact / Arial-Bold),
    kesinlikle BÜYÜK HARF (UPPERCASE), font_size=96 ve Drop Shadow (+6px kaydırılmış %80 opak siyah gölge)
    efektine sahip CompositeVideoClip altyazı katmanlarına dönüştürür.
    """
    subtitle_clips = []

    # Agresif ve kalın font seçimi: Sistemde varsa 'Impact', yoksa 'Arial-Bold'
    if os.path.exists("C:/Windows/Fonts/impact.ttf"):
        font_path = "C:/Windows/Fonts/impact.ttf"
    elif os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
        font_path = "C:/Windows/Fonts/arialbd.ttf"
    elif os.path.exists("C:/Windows/Fonts/arial.ttf"):
        font_path = "C:/Windows/Fonts/arial.ttf"
    else:
        font_path = None

    for start_sec, end_sec, text in subtitles:
        # Metni SADECE 1 veya maksimum 2 kelimelik parçalara ayır
        chunks = split_cue_into_shorts_chunks(start_sec, end_sec, text, max_words=2)

        for c_start, c_end, c_text in chunks:
            # 1-2 kelimelik metni tek satırda tut ve KESİNLİKLE BÜYÜK HARF yap (text.upper())
            c_text_clean = " ".join(c_text.strip().split()).upper()
            if not c_text_clean:
                continue

            duration = max(0.04, c_end - c_start)

            # 1. Drop Shadow (Gölge) katmanı: Siyah, opacity=0.8, x ve y koordinatlarında +6 piksel kaydırılmış
            shadow_clip = TextClip(
                font=font_path,
                text=c_text_clean,
                font_size=font_size,
                size=(960, None),
                margin=(0, 20),
                color="black",
                method="caption",
                text_align="center",
                horizontal_align="center",
                vertical_align="center",
                interline=6,
                duration=duration,
            )
            if hasattr(shadow_clip, "with_opacity"):
                shadow_clip = shadow_clip.with_opacity(0.8)
            elif hasattr(shadow_clip, "set_opacity"):
                shadow_clip = shadow_clip.set_opacity(0.8)

            if hasattr(shadow_clip, "with_position"):
                shadow_clip = shadow_clip.with_position((6, 6))
            elif hasattr(shadow_clip, "set_position"):
                shadow_clip = shadow_clip.set_position((6, 6))

            # 2. Ana metin katmanı: Beyaz renk
            main_clip = TextClip(
                font=font_path,
                text=c_text_clean,
                font_size=font_size,
                size=(960, None),
                margin=(0, 20),
                color="white",
                method="caption",
                text_align="center",
                horizontal_align="center",
                vertical_align="center",
                interline=6,
                duration=duration,
            )
            if hasattr(main_clip, "with_position"):
                main_clip = main_clip.with_position((0, 0))
            elif hasattr(main_clip, "set_position"):
                main_clip = main_clip.set_position((0, 0))

            w = max(main_clip.size[0], shadow_clip.size[0])
            h = max(main_clip.size[1], shadow_clip.size[1])

            # 3. İki TextClip katmanını CompositeVideoClip ile üst üste bindirerek gölgeli altyazı karesini oluştur
            sub_comp = CompositeVideoClip(
                [shadow_clip, main_clip],
                size=(w + 12, h + 12),
            )

            if hasattr(sub_comp, "with_start"):
                sub_comp = sub_comp.with_start(c_start)
            elif hasattr(sub_comp, "set_start"):
                sub_comp = sub_comp.set_start(c_start)

            if hasattr(sub_comp, "with_duration"):
                sub_comp = sub_comp.with_duration(duration)
            elif hasattr(sub_comp, "set_duration"):
                sub_comp = sub_comp.set_duration(duration)

            if hasattr(sub_comp, "with_position"):
                sub_comp = sub_comp.with_position(("center", 1080))
            elif hasattr(sub_comp, "set_position"):
                sub_comp = sub_comp.set_position(("center", 1080))

            subtitle_clips.append(sub_comp)

    return subtitle_clips


def ensure_vertical_aspect_ratio(clip, target_w: int = 1080, target_h: int = 1920):
    """Herhangi bir en-boy oranındaki videoyu 9:16 (1080x1920) dikey formata
    bozulma ve esneme olmadan (merkezden kırparak) dönüştürür.
    """
    w, h = clip.size
    if (w, h) == (target_w, target_h):
        return clip

    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Video daha geniş -> Yüksekliği 1920'ye ayarla, genişliği merkezden 1080'e kırp
        new_w = int(w * (target_h / h))
        if hasattr(clip, "resized"):
            scaled = clip.resized(height=target_h)
            x_center = scaled.size[0] / 2
            return scaled.cropped(
                x1=x_center - target_w / 2,
                x2=x_center + target_w / 2,
                y1=0,
                y2=target_h,
            )
        else:
            scaled = clip.resize(height=target_h)
            return scaled.crop(
                x_center=scaled.size[0] / 2,
                y_center=target_h / 2,
                width=target_w,
                height=target_h,
            )
    else:
        # Video daha dar -> Genişliği 1080'e ayarla, yüksekliği merkezden 1920'ye kırp
        new_h = int(h * (target_w / w))
        if hasattr(clip, "resized"):
            scaled = clip.resized(width=target_w)
            y_center = scaled.size[1] / 2
            return scaled.cropped(
                x1=0,
                x2=target_w,
                y1=y_center - target_h / 2,
                y2=y_center + target_h / 2,
            )
        else:
            scaled = clip.resize(width=target_w)
            return scaled.crop(
                x_center=target_w / 2,
                y_center=scaled.size[1] / 2,
                width=target_w,
                height=target_h,
            )


def create_final_video(
    audio_path: str = "output.mp3",
    bg_paths: list[str] | str = None,
    subtitle_path: str = "output.srt",
    music_path: str = "bg_music.mp3",
    output_path: str = "final_shorts.mp4",
    fps: int = 24,
    subtitle_font_size: int = 96,
    **kwargs,
) -> str:
    """Arka plan videolarını (Pixabay'den indirilen 3 video), ana seslendirmeyi,
    dinamik arka plan müziğini (varsa) ve kalın, gölgeli agresif altyazıları birleştirerek
    9:16 (1080x1920) formatında YouTube Shorts videosu oluşturur.

    - İndirilen videoları VideoFileClip ile yükler ve concatenate_videoclips ile uç uca ekler.
    - Videonun süresini tam olarak ses süresine göre ayarlar (kırpma veya döngü).
    - bg_music.mp3 mevcutsa sesini %12 seviyesine kısarak miksler.
    - Agresif, kalın (Impact / Arial-Bold), büyük harf ve drop shadow efektli altyazıları ekler.
    - CompositeVideoClip ile 1080x1920 boyutunda render eder.
    """
    if "bg_image_path" in kwargs and kwargs["bg_image_path"]:
        val = kwargs["bg_image_path"]
        bg_paths = [val] if isinstance(val, str) else val

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")

    print(f"\n[Video Kurgu] '{audio_path}' yükleniyor...")
    voiceover_clip = AudioFileClip(audio_path)
    audio_duration = voiceover_clip.duration
    print(f"[Video Kurgu] Ana seslendirme süresi: {audio_duration:.2f} saniye")

    # 1. Ses Miksajı (Audio Mixing) - Arka plan müziği kontrolü
    audio_clips_to_close = [voiceover_clip]
    final_audio = voiceover_clip

    if os.path.exists(music_path):
        try:
            print(f"[Ses Miksajı] Arka plan müziği bulundu: '{music_path}'")
            music_clip = AudioFileClip(music_path)
            audio_clips_to_close.append(music_clip)
            music_duration = music_clip.duration
            print(f"[Ses Miksajı] Orijinal müzik süresi: {music_duration:.2f} saniye")

            # Müzik sesini ana sesi bastırmayacak şekilde (%12) kıs
            print("[Ses Miksajı] Müzik ses seviyesi kısılıyor (%12)...")
            music_clip = apply_audio_volume(music_clip, 0.12)

            # Müziğin süresini videoya eşitle (uzunsa kes, kısaysa döngüye al)
            if music_duration >= audio_duration:
                print("[Ses Miksajı] Müzik sesten uzun, video süresine göre kesiliyor...")
                if hasattr(music_clip, "subclipped"):
                    music_clip = music_clip.subclipped(0, audio_duration)
                else:
                    music_clip = music_clip.subclip(0, audio_duration)
            else:
                print("[Ses Miksajı] Müzik sesten kısa, video bitene kadar döngüye alınıyor...")
                music_clip = apply_audio_loop(music_clip, audio_duration)

            # CompositeAudioClip ile ana seslendirme ve arka plan müziğini birleştir
            print("[Ses Miksajı] CompositeAudioClip ile ana seslendirme ve müzik birleştiriliyor...")
            composite_audio = CompositeAudioClip([voiceover_clip, music_clip])
            if hasattr(composite_audio, "with_duration"):
                composite_audio = composite_audio.with_duration(audio_duration)
            elif hasattr(composite_audio, "set_duration"):
                composite_audio = composite_audio.set_duration(audio_duration)

            final_audio = composite_audio
            audio_clips_to_close.append(final_audio)
            print("[Ses Miksajı] Ses miksajı başarıyla tamamlandı!")

        except Exception as music_err:
            print(f"[Ses Miksajı] Uyarı: Müzik işlenirken hata oluştu ({music_err}). Yalnızca ana seslendirme kullanılacak.")
            final_audio = voiceover_clip
    else:
        print(f"[Ses Miksajı] '{music_path}' bulunamadı. Sadece ana seslendirme (Voiceover) kullanılacak.")

    # 2. Arka plan kontrolü ve çoklu video birleştirme (Multi-Video Concatenation)
    if isinstance(bg_paths, str):
        candidate_bg_files = [bg_paths]
    elif isinstance(bg_paths, list):
        candidate_bg_files = bg_paths
    else:
        candidate_bg_files = ["bg_1.mp4", "bg_2.mp4", "bg_3.mp4", "background.mp4"]

    valid_bg_files = [f for f in candidate_bg_files if os.path.exists(f)]
    loaded_clips = []

    if valid_bg_files:
        print(f"[Video Kurgu] {len(valid_bg_files)} adet arka plan videosu bulundu: {valid_bg_files}")
        for video_path in valid_bg_files:
            try:
                clip = VideoFileClip(video_path)
                # Her bir videoyu 1080x1920 (9:16) formatına dönüştür
                clip = ensure_vertical_aspect_ratio(clip, 1080, 1920)
                loaded_clips.append(clip)
                print(f"[Video Kurgu] Video klip eklendi: '{video_path}' (Süre: {clip.duration:.2f}s)")
            except Exception as e:
                print(f"[Video Kurgu] Uyarı: '{video_path}' yüklenemedi ({e}). Diğer kliplerle devam ediliyor.")

    if loaded_clips:
        try:
            if len(loaded_clips) > 1:
                print(f"[Video Kurgu] {len(loaded_clips)} farklı arka plan klibi uç uca birleştiriliyor (concatenate_videoclips)...")
                video_clip = concatenate_videoclips(loaded_clips)
            else:
                video_clip = loaded_clips[0]
        except Exception as concat_err:
            print(f"[Video Kurgu] Klipler birleştirilirken hata oluştu ({concat_err}). İlk geçerli klip kullanılıyor...")
            video_clip = loaded_clips[0]

        bg_duration = video_clip.duration
        print(f"[Video Kurgu] Birleştirilmiş arka plan videosu toplam süresi: {bg_duration:.2f} saniye")

        if bg_duration >= audio_duration:
            print("[Video Kurgu] Birleştirilmiş video sesten uzun, video ses süresine göre kırpılıyor...")
            if hasattr(video_clip, "subclipped"):
                video_clip = video_clip.subclipped(0, audio_duration)
            else:
                video_clip = video_clip.subclip(0, audio_duration)
        else:
            print("[Video Kurgu] Birleştirilmiş video sesten kısa, video ses süresine kadar döngüye alınıyor...")
            if hasattr(video_clip, "with_effects") and hasattr(vfx, "Loop"):
                video_clip = video_clip.with_effects([vfx.Loop(duration=audio_duration)])
            elif hasattr(vfx, "loop"):
                video_clip = vfx.loop(video_clip, duration=audio_duration)
            else:
                n_loops = int(audio_duration // bg_duration) + 1
                video_clip = concatenate_videoclips([video_clip] * n_loops)
                if hasattr(video_clip, "subclipped"):
                    video_clip = video_clip.subclipped(0, audio_duration)
                else:
                    video_clip = video_clip.subclip(0, audio_duration)
    else:
        print("[Video Kurgu] Arka plan videosu bulunamadı. 1080x1920 koyu renkli statik ColorClip oluşturuluyor...")
        video_clip = ColorClip(
            size=(1080, 1920),
            color=(20, 24, 33),
            duration=audio_duration,
        )

    # 3. Mikslenen sesi videoya entegre et
    print("[Video Kurgu] Mikslenen ses arka plan videosuna entegre ediliyor...")
    if hasattr(video_clip, "with_audio"):
        video_clip = video_clip.with_audio(final_audio)
    elif hasattr(video_clip, "set_audio"):
        video_clip = video_clip.set_audio(final_audio)

    if hasattr(video_clip, "with_duration"):
        video_clip = video_clip.with_duration(audio_duration)
    elif hasattr(video_clip, "set_duration"):
        video_clip = video_clip.set_duration(audio_duration)

    # 4. Altyazıları oku ve kalın, agresif, gölgeli katmanlar olarak oluştur (Agresif Tipografi)
    layers = [video_clip]
    subtitle_clips = []

    sub_file_to_use = subtitle_path
    if not os.path.exists(sub_file_to_use):
        vtt_alt = os.path.splitext(subtitle_path)[0] + ".vtt"
        if os.path.exists(vtt_alt):
            sub_file_to_use = vtt_alt

    if os.path.exists(sub_file_to_use):
        print(f"[Video Kurgu] Altyazı dosyası okunuyor: '{sub_file_to_use}'...")
        subtitles = parse_subtitles(sub_file_to_use)
        print(f"[Video Kurgu] {len(subtitles)} altyazı bloğu bulundu. Agresif tipografi (UPPERCASE, font_size={subtitle_font_size}, Drop Shadow) altyazı katmanları oluşturuluyor...")
        subtitle_clips = create_subtitle_clips(subtitles, font_size=subtitle_font_size)
        layers.extend(subtitle_clips)
        print(f"[Video Kurgu] Toplam {len(subtitle_clips)} adet dinamik altyazı karesi hazırlandı.")
    else:
        print("[Video Kurgu] Uyarı: Altyazı dosyası bulunamadı, video altyazısız oluşturulacak.")

    # 5. CompositeVideoClip ile tüm katmanları birleştir
    print("[Video Kurgu] CompositeVideoClip ile video ve gölgeli altyazı katmanları birleştiriliyor...")
    final_clip = CompositeVideoClip(layers, size=(1080, 1920))
    if hasattr(final_clip, "with_duration"):
        final_clip = final_clip.with_duration(audio_duration)
    elif hasattr(final_clip, "set_duration"):
        final_clip = final_clip.set_duration(audio_duration)

    # 6. Nihai çıktıyı fps=24 ile kaydet
    print(f"[Video Kurgu] Nihai video render ediliyor: '{output_path}' (fps={fps})...")
    final_clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
    )

    # Kaynakları serbest bırak
    for sc in subtitle_clips:
        try:
            sc.close()
        except Exception:
            pass
    for ac in audio_clips_to_close:
        try:
            ac.close()
        except Exception:
            pass
    for lc in loaded_clips:
        try:
            lc.close()
        except Exception:
            pass
    try:
        video_clip.close()
    except Exception:
        pass
    try:
        final_clip.close()
    except Exception:
        pass

    print(f"[Video Kurgu] Başarılı! Nihai video oluşturuldu: {output_path}")
    return output_path


async def main():
    test_topic = "The FBI interrogation trick to spot a liar instantly"
    print(f"Generating viral Shorts script for: '{test_topic}'...\n")

    try:
        # 1. Generate viral script
        script = generate_shorts_script(test_topic)
        print("=== 1. GENERATED VIRAL SHORTS SCRIPT (ENGLISH) ===")
        print(script)
        print("\n" + "=" * 40 + "\n")

        # 2. Extract background search query & download 3 Pixabay background clips
        search_query = extract_search_query(script, default="dark")
        print("=== 2. PIXABAY MULTI-VIDEO BACKGROUND DOWNLOAD ===")
        print(f"Extracted search query: '{search_query}'")
        downloaded_bgs = download_background_video(search_query, count=3, output_prefix="bg")
        if downloaded_bgs:
            print(f"Using {len(downloaded_bgs)} downloaded Pixabay background videos: {downloaded_bgs}")
        else:
            print("Background videos could not be downloaded. Falling back to default background.")
        print("\n" + "=" * 40 + "\n")

        # 3. Extract spoken voiceover dialogue
        voiceover_text = extract_voiceover(script)
        print("=== 3. EXTRACTED VOICEOVER NARRATION ===")
        print(voiceover_text)
        print("\n" + "=" * 40 + "\n")

        # 4. Generate voiceover and time-synced subtitles via Edge TTS + SubMaker
        output_audio = "output.mp3"
        output_subtitle = "output.srt"
        print("Generating voiceover and time-synced subtitles (Voice: en-US-ChristopherNeural)...")
        await text_to_speech(
            voiceover_text,
            output_audio=output_audio,
            output_subtitle=output_subtitle,
            voice="en-US-ChristopherNeural",
        )
        print(f"Success! Audio: '{output_audio}', Subtitles: '{output_subtitle}' & '{os.path.splitext(output_subtitle)[0]}.vtt'")

        # 5. Video Editing, Audio Mixing & Captions Compositing
        print("\n" + "=" * 40)
        print("=== 5. VIDEO EDITING, AUDIO MIXING & CAPTIONS COMPOSITING ===")
        create_final_video(
            audio_path=output_audio,
            bg_paths=downloaded_bgs if downloaded_bgs else "background.mp4",
            subtitle_path=output_subtitle,
            music_path="bg_music.mp3",
            output_path="final_shorts.mp4",
            fps=24,
            subtitle_font_size=96,
        )

    except Exception as e:
        print(f"Error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
