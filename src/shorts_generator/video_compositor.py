"""MoviePy video compositing, dynamic typography, and audio mixing engine."""

import os
from typing import Optional, Union

# MoviePy import (compatible with both MoviePy 1.x and 2.x)
try:
    from moviepy.editor import (
        VideoFileClip,
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

from .config import (
    SYSTEM_FONT_PATH,
    AUDIO_DUCKING_VOLUME,
    TARGET_VIDEO_WIDTH,
    TARGET_VIDEO_HEIGHT,
    DEFAULT_FPS,
)
from .utils import parse_subtitles, split_cue_into_shorts_chunks


def apply_audio_volume(clip, factor: float):
    """Applies volume multiplier across MoviePy 1.x (volumex) and 2.x."""
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
    """Loops audio clip to target duration across MoviePy 1.x and 2.x."""
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


def ensure_vertical_aspect_ratio(
    clip, target_w: int = TARGET_VIDEO_WIDTH, target_h: int = TARGET_VIDEO_HEIGHT
):
    """Converts any video aspect ratio to 9:16 (1080x1920) via centered crop without distortion."""
    w, h = clip.size
    if (w, h) == (target_w, target_h):
        return clip

    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Video is wider -> scale height to 1920, center-crop width to 1080
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
        # Video is taller -> scale width to 1080, center-crop height to 1920
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


def create_subtitle_clips(
    subtitles: list[tuple[float, float, str]],
    font_size: int = 96,
) -> list[CompositeVideoClip]:
    """Generates aggressive uppercase drop-shadow subtitle layers formatted for 9:16 safe zones."""
    subtitle_clips = []
    font_path = SYSTEM_FONT_PATH

    for start_sec, end_sec, text in subtitles:
        chunks = split_cue_into_shorts_chunks(start_sec, end_sec, text, max_words=2)

        for c_start, c_end, c_text in chunks:
            c_text_clean = " ".join(c_text.strip().split()).upper()
            if not c_text_clean:
                continue

            duration = max(0.04, c_end - c_start)

            # Drop Shadow layer (80% opacity, +6px offset)
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

            # Main white foreground text layer
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


def create_final_video(
    audio_path: str = "output.mp3",
    bg_paths: Optional[Union[list[str], str]] = None,
    subtitle_path: str = "output.srt",
    music_path: str = "bg_music.mp3",
    output_path: str = "final_shorts.mp4",
    fps: int = DEFAULT_FPS,
    subtitle_font_size: int = 96,
    **kwargs,
) -> str:
    """Composites background clips, mixed voiceover + ducked music, and dynamic subtitles into 1080x1920 MP4."""
    if "bg_image_path" in kwargs and kwargs["bg_image_path"]:
        val = kwargs["bg_image_path"]
        bg_paths = [val] if isinstance(val, str) else val

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")

    print(f"\n[Video Kurgu] '{audio_path}' yükleniyor...")
    voiceover_clip = AudioFileClip(audio_path)
    audio_duration = voiceover_clip.duration
    print(f"[Video Kurgu] Ana seslendirme süresi: {audio_duration:.2f} saniye")

    audio_clips_to_close = [voiceover_clip]
    final_audio = voiceover_clip

    # 1. Background Music Mixing with ducking
    if os.path.exists(music_path):
        try:
            print(f"[Ses Miksajı] Arka plan müziği bulundu: '{music_path}'")
            music_clip = AudioFileClip(music_path)
            audio_clips_to_close.append(music_clip)
            music_duration = music_clip.duration
            print(f"[Ses Miksajı] Orijinal müzik süresi: {music_duration:.2f} saniye")

            print(f"[Ses Miksajı] Müzik ses seviyesi kısılıyor (%{int(AUDIO_DUCKING_VOLUME * 100)})...")
            music_clip = apply_audio_volume(music_clip, AUDIO_DUCKING_VOLUME)

            if music_duration >= audio_duration:
                if hasattr(music_clip, "subclipped"):
                    music_clip = music_clip.subclipped(0, audio_duration)
                else:
                    music_clip = music_clip.subclip(0, audio_duration)
            else:
                music_clip = apply_audio_loop(music_clip, audio_duration)

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

    # 2. Multi-video Background Concatenation & Pacing
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
                clip = ensure_vertical_aspect_ratio(clip, TARGET_VIDEO_WIDTH, TARGET_VIDEO_HEIGHT)
                loaded_clips.append(clip)
                print(f"[Video Kurgu] Video klip eklendi: '{video_path}' (Süre: {clip.duration:.2f}s)")
            except Exception as e:
                print(f"[Video Kurgu] Uyarı: '{video_path}' yüklenemedi ({e}). Diğer kliplerle devam ediliyor.")

    allocated_subclips = []
    if loaded_clips:
        num_clips = len(loaded_clips)
        target_slice = audio_duration / num_clips
        print(f"[Video Kurgu] {num_clips} adet sahne arka plan klibi video süresine göre dengeli paylaştırılıyor (~{target_slice:.2f}s her klip)...")

        for idx, clip in enumerate(loaded_clips):
            cur_target = target_slice if idx < num_clips - 1 else (audio_duration - (target_slice * (num_clips - 1)))
            cur_target = max(0.5, cur_target)

            if clip.duration >= cur_target:
                c_slice = clip.subclipped(0, cur_target) if hasattr(clip, "subclipped") else clip.subclip(0, cur_target)
            else:
                n_loops = int(cur_target // clip.duration) + 1
                looped = concatenate_videoclips([clip] * n_loops)
                c_slice = looped.subclipped(0, cur_target) if hasattr(looped, "subclipped") else looped.subclip(0, cur_target)
            allocated_subclips.append(c_slice)

        try:
            if len(allocated_subclips) > 1:
                video_clip = concatenate_videoclips(allocated_subclips)
            else:
                video_clip = allocated_subclips[0]
        except Exception as concat_err:
            print(f"[Video Kurgu] Klipler birleştirilirken hata oluştu ({concat_err}). İlk geçerli klip kullanılıyor...")
            video_clip = loaded_clips[0]
            if video_clip.duration >= audio_duration:
                video_clip = video_clip.subclipped(0, audio_duration) if hasattr(video_clip, "subclipped") else video_clip.subclip(0, audio_duration)
            else:
                n_loops = int(audio_duration // video_clip.duration) + 1
                looped = concatenate_videoclips([video_clip] * n_loops)
                video_clip = looped.subclipped(0, audio_duration) if hasattr(looped, "subclipped") else looped.subclip(0, audio_duration)
    else:
        print("[Video Kurgu] Arka plan videosu bulunamadı. 1080x1920 koyu renkli statik ColorClip oluşturuluyor...")
        video_clip = ColorClip(
            size=(TARGET_VIDEO_WIDTH, TARGET_VIDEO_HEIGHT),
            color=(20, 24, 33),
            duration=audio_duration,
        )

    # 3. Audio Attachment
    if hasattr(video_clip, "with_audio"):
        video_clip = video_clip.with_audio(final_audio)
    elif hasattr(video_clip, "set_audio"):
        video_clip = video_clip.set_audio(final_audio)

    if hasattr(video_clip, "with_duration"):
        video_clip = video_clip.with_duration(audio_duration)
    elif hasattr(video_clip, "set_duration"):
        video_clip = video_clip.set_duration(audio_duration)

    # 4. Subtitle Layers
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
        print(f"[Video Kurgu] {len(subtitles)} altyazı bloğu bulundu. Agresif tipografi altyazı katmanları oluşturuluyor...")
        subtitle_clips = create_subtitle_clips(subtitles, font_size=subtitle_font_size)
        layers.extend(subtitle_clips)
        print(f"[Video Kurgu] Toplam {len(subtitle_clips)} adet dinamik altyazı karesi hazırlandı.")
    else:
        print("[Video Kurgu] Uyarı: Altyazı dosyası bulunamadı, video altyazısız oluşturulacak.")

    # 5. Composite Layers
    final_clip = CompositeVideoClip(layers, size=(TARGET_VIDEO_WIDTH, TARGET_VIDEO_HEIGHT))
    if hasattr(final_clip, "with_duration"):
        final_clip = final_clip.with_duration(audio_duration)
    elif hasattr(final_clip, "set_duration"):
        final_clip = final_clip.set_duration(audio_duration)

    # 6. Render Output
    print(f"[Video Kurgu] Nihai video render ediliyor: '{output_path}' (fps={fps})...")
    final_clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
    )

    # Release resources
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
    for asc in allocated_subclips:
        try:
            asc.close()
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
