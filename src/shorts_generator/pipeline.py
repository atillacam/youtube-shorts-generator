"""End-to-end pipeline orchestrator for AI Shorts generation."""

import os
import json
import shutil
from datetime import datetime
from typing import Optional, Callable

from .config import (
    DEFAULT_VOICE,
    DEFAULT_BG_COUNT,
    DEFAULT_OUTPUT_FILENAME,
    DEFAULT_BG_MUSIC,
    DEFAULT_FONT_SIZE,
    DEFAULT_FPS,
)
from .models import PipelineResult
from .utils import slugify_text
from .script_generator import (
    generate_shorts_script,
    generate_youtube_metadata,
    extract_scene_search_queries,
    extract_voiceover,
)
from .downloader import download_scene_background_videos
from .tts_engine import text_to_speech
from .video_compositor import create_final_video


class ShortsPipeline:
    """Orchestrates end-to-end creation of automated YouTube Shorts and TikToks."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        bg_count: int = DEFAULT_BG_COUNT,
        music_path: str = DEFAULT_BG_MUSIC,
        font_size: int = DEFAULT_FONT_SIZE,
        fps: int = DEFAULT_FPS,
        output_dir_base: str = "outputs",
    ):
        self.voice = voice
        self.bg_count = bg_count
        self.music_path = music_path
        self.font_size = font_size
        self.fps = fps
        self.output_dir_base = output_dir_base

    async def run(
        self,
        topic: str,
        quick_output_path: str = DEFAULT_OUTPUT_FILENAME,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> PipelineResult:
        """Executes full automated pipeline for given video topic.

        Returns:
            PipelineResult: Summary metadata and artifact paths produced during execution.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = slugify_text(topic)
        project_dir = os.path.join(self.output_dir_base, f"{timestamp_str}_{slug}")

        bg_dir = os.path.join(project_dir, "backgrounds")
        os.makedirs(bg_dir, exist_ok=True)

        project_video_path = os.path.join(project_dir, "video.mp4")
        project_meta_path = os.path.join(project_dir, "metadata.json")
        project_script_path = os.path.join(project_dir, "script.txt")
        project_audio_path = os.path.join(project_dir, "voiceover.mp3")
        project_sub_path = os.path.join(project_dir, "subtitles.srt")

        print(f"\n{'=' * 60}")
        print(f"🎬 AI YouTube Shorts Generator Başlatılıyor")
        print(f"📌 Konu: '{topic}'")
        print(f"📁 Proje Klasörü: '{project_dir}'")
        print(f"🎙️ Ses Modeli: '{self.voice}'")
        print(f"🎞️ Sahne Klip Sayısı: {self.bg_count}")
        print(f"📁 Hızlı Erişim Çıktısı: '{quick_output_path}'")
        print(f"{'=' * 60}\n")

        # 1. Script Generation
        if progress_callback:
            progress_callback("Generating script", 15)
        script = generate_shorts_script(topic)
        print("=== 1. GENERATED VIRAL SHORTS SCRIPT (ENGLISH) ===")
        print(script)
        with open(project_script_path, "w", encoding="utf-8") as f_s:
            f_s.write(script)
        print(f"💾 Senaryo arşivlendi: '{project_script_path}'\n")

        # 2. YouTube SEO Metadata
        if progress_callback:
            progress_callback("Generating SEO metadata", 30)
        print("=== 2. GENERATING YOUTUBE SEO METADATA ===")
        metadata = generate_youtube_metadata(topic, script)
        with open(project_meta_path, "w", encoding="utf-8") as f_meta:
            json.dump(metadata, f_meta, ensure_ascii=False, indent=2)

        root_meta_file = os.path.splitext(quick_output_path)[0] + "_metadata.json"
        with open(root_meta_file, "w", encoding="utf-8") as f_meta_root:
            json.dump(metadata, f_meta_root, ensure_ascii=False, indent=2)

        print(f"📌 Başlık: {metadata.get('title')}")
        print(f"📝 Açıklama: {metadata.get('description')}")
        print(f"🏷️ Etiketler: {', '.join(metadata.get('tags', []))}")
        print(f"💾 Metadata kaydedildi: '{project_meta_path}' ve '{root_meta_file}'\n")

        if dry_run:
            if progress_callback:
                progress_callback("Dry run complete", 100)
            print("[Dry Run] Senaryo ve metadata üretimi tamamlandı. Video işleme adımları atlanıyor.")
            return PipelineResult(
                topic=topic,
                project_dir=project_dir,
                video_path="",
                quick_output_path=quick_output_path,
                metadata_path=project_meta_path,
                metadata=metadata,
                script=script,
            )

        # 3. Pixabay Multi-Scene Background Downloads
        if progress_callback:
            progress_callback("Downloading background footage", 50)
        scene_queries = extract_scene_search_queries(script, topic=topic)
        print("=== 3. MULTI-SCENE BACKGROUND VIDEO DISCOVERY & DOWNLOAD ===")
        print(f"Extracted Scene Queries: {scene_queries}")
        downloaded_bgs = download_scene_background_videos(
            scene_queries, output_dir=bg_dir, count=self.bg_count
        )
        if downloaded_bgs:
            print(f"Using {len(downloaded_bgs)} distinct background scene videos: {downloaded_bgs}\n")
        else:
            print("Background videos could not be downloaded. Falling back to default background.\n")

        # 4. Spoken Narration Extraction
        if progress_callback:
            progress_callback("Extracting spoken narration", 65)
        voiceover_text = extract_voiceover(script)
        print("=== 4. EXTRACTED VOICEOVER NARRATION ===")
        print(voiceover_text)
        print("\n" + "=" * 40 + "\n")

        # 5. Voiceover Synthesis & Synchronized Subtitles
        if progress_callback:
            progress_callback("Synthesizing voiceover and subtitles", 80)
        print(f"Generating voiceover and time-synced subtitles (Voice: {self.voice})...")
        await text_to_speech(
            voiceover_text,
            output_audio=project_audio_path,
            output_subtitle=project_sub_path,
            voice=self.voice,
        )

        try:
            shutil.copyfile(project_audio_path, "output.mp3")
            shutil.copyfile(project_sub_path, "output.srt")
            project_vtt = os.path.splitext(project_sub_path)[0] + ".vtt"
            if os.path.exists(project_vtt):
                shutil.copyfile(project_vtt, "output.vtt")
        except Exception:
            pass

        print(f"Success! Audio: '{project_audio_path}', Subtitles: '{project_sub_path}'\n")

        # 6. Video Compositing & Captions
        if progress_callback:
            progress_callback("Rendering video and compositing captions", 95)
        print("=== 6. VIDEO EDITING, AUDIO MIXING & CAPTIONS COMPOSITING ===")
        create_final_video(
            audio_path=project_audio_path,
            bg_paths=downloaded_bgs if downloaded_bgs else "background.mp4",
            subtitle_path=project_sub_path,
            music_path=self.music_path,
            output_path=project_video_path,
            fps=self.fps,
            subtitle_font_size=self.font_size,
        )

        try:
            if os.path.abspath(project_video_path) != os.path.abspath(quick_output_path):
                shutil.copyfile(project_video_path, quick_output_path)
        except Exception:
            pass

        if progress_callback:
            progress_callback("Complete", 100)

        print("\n🎉 Tüm süreç başarıyla tamamlandı!")
        print(f"🎬 Konuya Özel Video: {project_video_path}")
        print(f"📁 Proje Arşiv Klasörü: {project_dir}")
        print(f"🚀 Hızlı Erişim: {quick_output_path}")
        print(f"📋 YouTube Metadata: {project_meta_path}")

        return PipelineResult(
            topic=topic,
            project_dir=project_dir,
            video_path=project_video_path,
            quick_output_path=quick_output_path,
            metadata_path=project_meta_path,
            metadata=metadata,
            script=script,
        )

