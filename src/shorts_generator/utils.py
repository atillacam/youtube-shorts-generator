"""Text parsing, slugification, and subtitle manipulation utilities."""

import os
import re


def slugify_text(text: str) -> str:
    """Türkçe karakterleri dönüştürerek dosya sistemine ve URL'lere uygun temiz slug üretir.

    Converts Turkish characters and non-alphanumeric symbols to clean kebab-case slug.
    """
    tr_map = str.maketrans({
        "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
        "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u"
    })
    cleaned = text.translate(tr_map).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return cleaned[:45] if cleaned else "shorts"


def clean_subtitle_text(text: str) -> str:
    """Strips markdown syntax, emojis, and unwanted formatting from subtitle strings."""
    if not text:
        return ""
    # Strip markdown bold/italic/backtick/tags
    cleaned = re.sub(r"[\*_#`~]", "", text)
    # Remove bracketed cues like [Applause] or (Laughs)
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", cleaned)
    # Remove emojis and high unicode pictorial symbols
    cleaned = re.sub(
        r"[\U00010000-\U0010ffff]",
        "",
        cleaned,
        flags=re.UNICODE,
    )
    # Normalize whitespaces
    return re.sub(r"\s+", " ", cleaned).strip()


def estimate_narration_duration(text: str, words_per_minute: int = 150) -> float:
    """Calculates approximate speech duration in seconds for a given narration script."""
    words = text.split()
    if not words:
        return 0.0
    return round((len(words) / words_per_minute) * 60.0, 2)



def srt_to_vtt(srt_content: str) -> str:
    """SRT biçimindeki altyazı içeriğini standart WebVTT formatına dönüştürür.

    Converts SRT comma timestamps (00:00:01,500) to WebVTT format (00:00:01.500).
    """
    vtt_lines = ["WEBVTT\n"]
    for line in srt_content.strip().splitlines():
        if "-->" in line:
            vtt_lines.append(line.replace(",", "."))
        else:
            vtt_lines.append(line)
    return "\n".join(vtt_lines) + "\n"


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

    if len(words) <= max_words:
        return [(start, end, text.strip())]

    chunks = []
    i = 0
    while i < len(words):
        w1 = words[i]
        if i + 1 >= len(words):
            chunks.append([w1])
            i += 1
        else:
            w2 = words[i + 1]
            if any(w1.endswith(p) for p in [".", ",", "!", "?", ":", ";", "—", "-"]):
                chunks.append([w1])
                i += 1
            else:
                chunks.append([w1, w2])
                i += 2

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
