"""🎬 AI YouTube Shorts & TikTok Generator - Automated Video Production Pipeline.

Main entry point and CLI runner.
"""

import sys
import argparse
import asyncio

# Expose all core functions at root module level for complete backward compatibility
from src.shorts_generator.config import (
    DEFAULT_VOICE,
    DEFAULT_BG_COUNT,
    DEFAULT_OUTPUT_FILENAME,
    DEFAULT_BG_MUSIC,
    DEFAULT_FONT_SIZE,
    DEFAULT_FPS,
    GEMINI_API_KEY,
    PIXABAY_API_KEY,
    validate_environment,
    SUBTITLE_STYLE_PRESETS,
)
from src.shorts_generator.utils import (
    slugify_text,
    srt_to_vtt,
    parse_subtitles,
    split_cue_into_shorts_chunks,
)
from src.shorts_generator.script_generator import (
    call_gemini,
    generate_shorts_script,
    extract_scene_search_queries,
    extract_search_query,
    extract_voiceover,
    generate_youtube_metadata,
)
from src.shorts_generator.downloader import (
    download_scene_background_videos,
    download_background_video,
)
from src.shorts_generator.tts_engine import (
    text_to_speech,
    get_available_voice_aliases,
)

from src.shorts_generator.video_compositor import (
    apply_audio_volume,
    apply_audio_loop,
    ensure_vertical_aspect_ratio,
    create_subtitle_clips,
    create_final_video,
)
from src.shorts_generator.pipeline import ShortsPipeline

__all__ = [
    "slugify_text",
    "srt_to_vtt",
    "parse_subtitles",
    "split_cue_into_shorts_chunks",
    "call_gemini",
    "generate_shorts_script",
    "extract_scene_search_queries",
    "extract_search_query",
    "extract_voiceover",
    "generate_youtube_metadata",
    "download_scene_background_videos",
    "download_background_video",
    "text_to_speech",
    "apply_audio_volume",
    "apply_audio_loop",
    "ensure_vertical_aspect_ratio",
    "create_subtitle_clips",
    "create_final_video",
    "ShortsPipeline",
    "parse_arguments",
    "main",
]


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments for automated Shorts production."""
    parser = argparse.ArgumentParser(
        description="🎬 AI YouTube Shorts & TikTok Generator - Automated Video Production Pipeline"
    )
    parser.add_argument(
        "-t",
        "--topic",
        type=str,
        default=None,
        help="Video topic (e.g. 'How AI is revolutionizing software development'). If omitted, prompts interactively.",
    )
    parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default=DEFAULT_VOICE,
        help=f"Edge-TTS voice model or alias (default: {DEFAULT_VOICE}, or e.g. en-us-male, tr-male).",
    )
    parser.add_argument(
        "-c",
        "--bg-count",
        type=int,
        default=DEFAULT_BG_COUNT,
        help=f"Number of background video clips to download from Pixabay (default: {DEFAULT_BG_COUNT}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILENAME,
        help=f"Output video file path (default: {DEFAULT_OUTPUT_FILENAME}).",
    )
    parser.add_argument(
        "-m",
        "--music",
        type=str,
        default=DEFAULT_BG_MUSIC,
        help=f"Path to background music file (default: {DEFAULT_BG_MUSIC}).",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=DEFAULT_FONT_SIZE,
        help=f"Subtitle typography font size (default: {DEFAULT_FONT_SIZE}).",
    )
    parser.add_argument(
        "--style-preset",
        type=str,
        default="viral_yellow",
        choices=list(SUBTITLE_STYLE_PRESETS.keys()),
        help="Caption typography preset (choices: viral_yellow, tiktok_cyan, classic_white, alert_red).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate script and SEO metadata without downloading footage or rendering video.",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Display list of friendly voice aliases and exit.",
    )
    parser.add_argument(
        "--validate-env",
        action="store_true",
        help="Check presence of Gemini and Pixabay API keys and exit.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without interactive prompt when topic is omitted, using default topic.",
    )
    return parser.parse_args()


async def main():
    args = parse_arguments()

    if args.list_voices:
        print("\n🎙️ Desteklenen Ses Modelleri ve Kısayol Etiketleri:")
        for alias, voice_id in get_available_voice_aliases().items():
            print(f"  - {alias:<14} -> {voice_id}")
        return

    if args.validate_env:
        status = validate_environment()
        print("\n🔑 API Ortam Değişkeni Doğrulama:")
        print(f"  - GEMINI_API_KEY  : {'✅ Yapılandırıldı' if status['gemini_configured'] else '❌ Eksik'}")
        print(f"  - PIXABAY_API_KEY : {'✅ Yapılandırıldı' if status['pixabay_configured'] else '❌ Eksik'}")
        return

    default_topic = "How AI is revolutionizing software development"

    topic = args.topic
    if not topic:
        if args.non_interactive or not sys.stdin.isatty():
            topic = default_topic
            print(f"[CLI] Konu belirtilmedi, varsayılan konu seçildi: '{topic}'")
        else:
            try:
                user_input = input(
                    f"\n🎥 Shorts video konusunu girin (Varsayılan için Enter: '{default_topic}'): "
                ).strip()
                topic = user_input if user_input else default_topic
            except (EOFError, KeyboardInterrupt):
                topic = default_topic

    pipeline = ShortsPipeline(
        voice=args.voice,
        bg_count=args.bg_count,
        music_path=args.music,
        font_size=args.font_size,
        fps=DEFAULT_FPS,
    )

    try:
        await pipeline.run(
            topic=topic,
            quick_output_path=args.output,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"Error occurred during generation: {e}")


if __name__ == "__main__":
    asyncio.run(main())

