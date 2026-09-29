import os
import sys
import re
import textwrap
import asyncio
import urllib.request
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import edge_tts

# MoviePy importu (MoviePy 1.x ve 2.x sürümleriyle tam uyumlu)
try:
    from moviepy.editor import (
        VideoFileClip,
        AudioFileClip,
        ColorClip,
        TextClip,
        CompositeVideoClip,
        CompositeAudioClip,
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
        AudioFileClip,
        ColorClip,
        TextClip,
        CompositeVideoClip,
        CompositeAudioClip,
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
You are an expert viral content creator specializing in high-retention YouTube Shorts and TikTok videos.

Write the script entirely in English, keeping the tone highly engaging, mysterious, and perfect for a viral YouTube Short. Do not include any Turkish words.

Topic: {topic}

The script MUST follow this exact 3-part structure (around 30-40 seconds of speaking time):
1. [0-3s] Hook: An irresistible, scroll-stopping first sentence that triggers extreme curiosity and keeps viewers watching.
2. [3-25s] Body: 2-3 jaw-dropping facts or insights delivered rapidly with high energy and zero fluff.
3. [25-30s] Call to Action (CTA): A compelling psychological question prompting comments and subscriptions.

For each section, you MUST use this exact format:
- Visual: [Description of fast-paced visuals, footage, or on-screen animations]
- Voiceover: [The exact words the voiceover narrator speaks aloud]

CRITICAL RULES:
- Write exclusively in English.
- Voiceover lines must contain ONLY spoken dialogue. Never include bracketed directions, emojis, or sound effect markers inside Voiceover lines.
- At the very end of your response, on a new line, add exactly:
SEARCH_QUERY: [A single English word representing the core visual theme of the video to find matching background footage, e.g., robot, technology, city, coding, money]
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


def extract_search_query(script: str, default: str = "technology") -> str:
    """Senaryonun altındaki SEARCH_QUERY etiketinden arka plan arama terimini ayıklar."""
    match = re.search(r"SEARCH_QUERY\s*:\s*\[?([a-zA-Z0-9_\-]+)\]?", script, re.IGNORECASE)
    if match:
        query = match.group(1).strip().lower()
        if query:
            return query
    return default


def download_background_video(query: str, output_path: str = "background.mp4") -> str | None:
    """Pixabay Video API kullanarak belirtilen arama sorgusuna uygun kaliteli bir arka plan
    videosu bulur ve 'background.mp4' olarak indirir.

    Args:
        query: İngilizce arama terimi (örn. 'technology', 'robot', 'city').
        output_path: İndirilecek video dosyası yolu (varsayılan: background.mp4).

    Returns:
        str | None: İndirilen video dosyasının yolu veya başarısız olursa None.
    """
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        print("[Pixabay] Uyarı: PIXABAY_API_KEY ortam değişkeni bulunamadı (.env dosyasını kontrol edin).")
        return None

    clean_query = query.strip().replace("[", "").replace("]", "")
    print(f"\n[Pixabay] '{clean_query}' araması için arka plan videosu sorgulanıyor...")

    api_url = "https://pixabay.com/api/videos/"
    params = {
        "key": api_key,
        "q": clean_query,
        "video_type": "film",
        "per_page": 10,
        "safesearch": "true",
    }

    try:
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits", [])

        # Eğer sorgu ile sonuç bulunamadıysa popüler genel bir sorgu ile dene
        if not hits:
            print(f"[Pixabay] '{clean_query}' için video bulunamadı. Genel 'technology' sorgusu deneniyor...")
            params["q"] = "technology"
            response = requests.get(api_url, params=params, timeout=15)
            data = response.json()
            hits = data.get("hits", [])

        if not hits:
            print("[Pixabay] Uyarı: Hiçbir arka plan videosu bulunamadı.")
            return None

        # 1. Öncelik: Dikey (Portrait) videoları ara (height > width)
        selected_url = None
        for hit in hits:
            videos = hit.get("videos", {})
            for quality in ("large", "medium", "small"):
                info = videos.get(quality)
                if info and info.get("height", 0) > info.get("width", 0) and info.get("url"):
                    selected_url = info["url"]
                    print(f"[Pixabay] Dikey (9:16) formatta video bulundu ({info['width']}x{info['height']}).")
                    break
            if selected_url:
                break

        # 2. Öncelik: Dikey bulunamazsa en kaliteli yatay videoyu seç (otomatik 1080x1920'ye kırpılacak)
        if not selected_url:
            for hit in hits:
                videos = hit.get("videos", {})
                for quality in ("large", "medium", "small"):
                    info = videos.get(quality)
                    if info and info.get("url"):
                        selected_url = info["url"]
                        print(f"[Pixabay] Yüksek kaliteli video seçildi ({info['width']}x{info['height']}).")
                        break
                if selected_url:
                    break

        if not selected_url:
            print("[Pixabay] Uyarı: Geçerli bir video indirme bağlantısı bulunamadı.")
            return None

        # Videoyu güvenli akışla indir
        print("[Pixabay] Video indiriliyor...")
        downloaded = False
        try:
            r = requests.get(selected_url, stream=True, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                downloaded = True
        except Exception:
            downloaded = False

        if not downloaded:
            req = urllib.request.Request(selected_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req) as resp, open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            downloaded = True

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[Pixabay] Başarılı! Video kaydedildi: '{output_path}' ({file_size_mb:.2f} MB)")
        return output_path

    except Exception as e:
        print(f"[Pixabay] Arka plan videosu indirilirken hata oluştu: {e}")
        return None


def extract_voiceover(script: str) -> str:
    """Üretilen senaryo metninden yalnızca seslendirilecek kısımları (Voiceover) ayıklar.

    'Visual:', 'Hook:', 'CTA:', 'SEARCH_QUERY:', 'Görsel:' gibi yönlendirmeleri, sahne açıklamalarını
    ve zaman damgalarını sese dahil etmemek için temizler.
    """
    # 1. Aşama: 'Voiceover:' veya 'Seslendirme:' etiketli blokları yakala
    prefix = r"(?:^|\n)\s*(?:[-*•#\d\.\(\)]+\s*)?(?:\*\*|\*)?(?:Voiceover|Voice-over|Narration|Voice|Seslendirme|Dış\s*Ses|Ses|Metin)(?:\*\*|\*)?\s*:\s*"
    delimiter = r"(?=(?:\n\s*(?:[-*•#\d\.\(\)]+\s*)?(?:\*\*|\*)?(?:Visual|Visuals|Scene|Video|Voiceover|Voice-over|Narration|Voice|Hook|Body|CTA|Call\s*to\s*Action|SEARCH_QUERY|Görsel|Seslendirme|Dış\s*Ses|Kanca|Gövde|Kapanış|Sahne|\d+[\.\)])|\Z))"
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
    start: float, end: float, text: str, max_words: int = 6
) -> list[tuple[float, float, str]]:
    """Uzun cümleleri YouTube Shorts dinamiğine uygun 4-6 kelimelik kısa ve vurucu
    parçalara bölerek sürelerini orantısal olarak dağıtır.
    """
    words = text.split()
    if len(words) <= max_words:
        return [(start, end, text)]

    total_chars = sum(len(w) for w in words)
    duration = end - start

    chunks = []
    current_chunk = []
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= max_words:
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        if len(chunks) > 0 and len(current_chunk) <= 2:
            chunks[-1].extend(current_chunk)
        else:
            chunks.append(current_chunk)

    sub_cues = []
    cur_start = start
    for i, chk in enumerate(chunks):
        chk_text = " ".join(chk)
        chk_chars = sum(len(w) for w in chk)
        if i == len(chunks) - 1:
            chk_end = end
        else:
            chk_duration = duration * (chk_chars / total_chars)
            chk_end = cur_start + chk_duration
        sub_cues.append((cur_start, chk_end, chk_text))
        cur_start = chk_end

    return sub_cues


def create_subtitle_clips(
    subtitles: list[tuple[float, float, str]],
) -> list[TextClip]:
    """Zaman damgalı altyazı listesini YouTube Shorts dinamiklerine uygun olarak
    büyük, kalın (Bold), beyaz ve 5px siyah konturlu stilize TextClip nesnelerine dönüştürür.
    """
    subtitle_clips = []

    # Windows sistemindeki Arial Bold yazı tipi (kalın ve yüksek kontrastlı)
    font_path = "C:/Windows/Fonts/arialbd.ttf" if os.path.exists("C:/Windows/Fonts/arialbd.ttf") else None

    for start_sec, end_sec, text in subtitles:
        # Cümleyi 4-6 kelimelik parçalara ayırarak ekranda hızlı ve dinamik değişmesini sağla
        chunks = split_cue_into_shorts_chunks(start_sec, end_sec, text, max_words=6)

        for c_start, c_end, c_text in chunks:
            duration = max(0.2, c_end - c_start)
            # En fazla 2 satırda toplanması için metni sar
            wrapped = textwrap.fill(c_text, width=22)

            tc = (
                TextClip(
                    font=font_path,
                    text=wrapped,
                    font_size=66,
                    color="white",
                    stroke_color="black",
                    stroke_width=5,
                    text_align="center",
                    horizontal_align="center",
                    vertical_align="center",
                    duration=duration,
                )
                .with_start(c_start)
                .with_position(("center", 1080))  # Ekran ortasının hemen altı (Shorts safe zone)
            )
            subtitle_clips.append(tc)

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
    bg_path: str = "background.mp4",
    subtitle_path: str = "output.srt",
    music_path: str = "bg_music.mp3",
    output_path: str = "final_shorts.mp4",
    fps: int = 24,
) -> str:
    """Arka plan videosunu, ana seslendirmeyi, dinamik arka plan müziğini (varsa)
    ve stilize altyazıları birleştirerek 9:16 (1080x1920) formatında YouTube Shorts videosu oluşturur.

    - Eğer `background.mp4` yoksa, 1080x1920 boyutunda koyu renkli statik bir ColorClip oluşturur.
    - `output.mp3` ses dosyasını yükler ve süresini ölçer.
    - `bg_music.mp3` mevcutsa sesini %12 seviyesine kısar, video süresine göre keser veya döngüye alır
      ve CompositeAudioClip ile ana seslendirmeyle birleştirir.
    - Video süresini tam olarak ses süresine göre ayarlar (kırpma veya loop).
    - Mikslenen sesi videoya entegre eder (with_audio / set_audio).
    - `output.srt` (veya .vtt) dosyasından altyazıları okur ve ekranın ortasına stilize katman olarak ekler.
    - CompositeVideoClip ile tüm katmanları birleştirir.
    - Çıktıyı fps=24 ile `final_shorts.mp4` olarak kaydeder.
    """
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

    # 2. Arka plan kontrolü (background.mp4 var mı?)
    if os.path.exists(bg_path):
        print(f"[Video Kurgu] Arka plan videosu bulundu: '{bg_path}'")
        video_clip = VideoFileClip(bg_path)
        bg_duration = video_clip.duration
        print(f"[Video Kurgu] Mevcut video süresi: {bg_duration:.2f} saniye")

        if bg_duration >= audio_duration:
            print("[Video Kurgu] Video sesten uzun, video ses süresine kırpılıyor...")
            if hasattr(video_clip, "subclipped"):
                video_clip = video_clip.subclipped(0, audio_duration)
            else:
                video_clip = video_clip.subclip(0, audio_duration)
        else:
            print("[Video Kurgu] Video sesten kısa, video ses süresine kadar loop ediliyor...")
            if hasattr(video_clip, "with_effects") and hasattr(vfx, "Loop"):
                video_clip = video_clip.with_effects([vfx.Loop(duration=audio_duration)])
            elif hasattr(vfx, "loop"):
                video_clip = vfx.loop(video_clip, duration=audio_duration)
            else:
                n_loops = int(audio_duration // bg_duration) + 1
                from moviepy import concatenate_videoclips
                video_clip = concatenate_videoclips([video_clip] * n_loops)
                if hasattr(video_clip, "subclipped"):
                    video_clip = video_clip.subclipped(0, audio_duration)
                else:
                    video_clip = video_clip.subclip(0, audio_duration)

        # 9:16 (1080x1920) dikey format garantisi
        video_clip = ensure_vertical_aspect_ratio(video_clip, 1080, 1920)
    else:
        print(f"[Video Kurgu] '{bg_path}' bulunamadı. 1080x1920 koyu renkli statik ColorClip oluşturuluyor...")
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

    # 4. Altyazıları oku ve stilize katmanlar olarak oluştur
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
        print(f"[Video Kurgu] {len(subtitles)} altyazı bloğu bulundu. Stilize TextClip katmanları oluşturuluyor...")
        subtitle_clips = create_subtitle_clips(subtitles)
        layers.extend(subtitle_clips)
        print(f"[Video Kurgu] Toplam {len(subtitle_clips)} adet dinamik altyazı karesi hazırlandı.")
    else:
        print("[Video Kurgu] Uyarı: Altyazı dosyası bulunamadı, video altyazısız oluşturulacak.")

    # 5. CompositeVideoClip ile tüm katmanları birleştir
    print("[Video Kurgu] CompositeVideoClip ile video ve altyazı katmanları birleştiriliyor...")
    final_clip = CompositeVideoClip(layers)
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
    test_topic = "The 3 most shocking jobs AI will replace first"
    print(f"Generating viral Shorts script for: '{test_topic}'...\n")

    try:
        # 1. Senaryoyu üret
        script = generate_shorts_script(test_topic)
        print("=== 1. GENERATED VIRAL SHORTS SCRIPT (ENGLISH) ===")
        print(script)
        print("\n" + "=" * 40 + "\n")

        # 2. Arka plan arama terimini ayıkla ve Pixabay'den ilgili videoyu indir
        bg_video_path = "background.mp4"
        search_query = extract_search_query(script, default="technology")
        print("=== 2. PIXABAY BACKGROUND VIDEO DOWNLOAD ===")
        print(f"Extracted search query: '{search_query}'")
        downloaded_bg = download_background_video(search_query, output_path=bg_video_path)
        if downloaded_bg:
            print(f"Using downloaded Pixabay background video: '{bg_video_path}'")
        else:
            print("Background video could not be downloaded. Falling back to default background.")
        print("\n" + "=" * 40 + "\n")

        # 3. Sadece seslendirilecek metni ayıkla
        voiceover_text = extract_voiceover(script)
        print("=== 3. EXTRACTED VOICEOVER NARRATION ===")
        print(voiceover_text)
        print("\n" + "=" * 40 + "\n")

        # 4. Metni Edge TTS + SubMaker ile ses ve altyazı olarak kaydet
        output_audio = "output.mp3"
        output_subtitle = "output.srt"
        print(f"Generating voiceover and time-synced subtitles (Voice: en-US-ChristopherNeural)...")
        await text_to_speech(
            voiceover_text,
            output_audio=output_audio,
            output_subtitle=output_subtitle,
            voice="en-US-ChristopherNeural",
        )
        print(f"Success! Audio: '{output_audio}', Subtitles: '{output_subtitle}' & '{os.path.splitext(output_subtitle)[0]}.vtt'")

        # 5. Altyazılı Video Kurgu, Ses Miksajı ve Birleştirme
        print("\n" + "=" * 40)
        print("=== 5. VIDEO EDITING, AUDIO MIXING & CAPTIONS COMPOSITING ===")
        create_final_video(
            audio_path=output_audio,
            bg_path=bg_video_path,
            subtitle_path=output_subtitle,
            music_path="bg_music.mp3",
            output_path="final_shorts.mp4",
            fps=24,
        )

    except Exception as e:
        print(f"Hata oluştu: {e}")


if __name__ == "__main__":
    asyncio.run(main())
