"""Project configuration and environment settings."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Base directory paths
PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Load environment variables from project root .env
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# Gemini Models Fallback Chain
DEFAULT_GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

# Audio & Voice Settings
DEFAULT_VOICE = "en-US-ChristopherNeural"
FALLBACK_VOICE = "en-GB-RyanNeural"
AUDIO_DUCKING_VOLUME = 0.12

# Video & Render Settings
TARGET_VIDEO_WIDTH = 1080
TARGET_VIDEO_HEIGHT = 1920
DEFAULT_FPS = 24
DEFAULT_BG_COUNT = 3
DEFAULT_FONT_SIZE = 96
DEFAULT_OUTPUT_FILENAME = "final_shorts.mp4"
DEFAULT_BG_MUSIC = "bg_music.mp3"


# Subtitle Style Presets
SUBTITLE_STYLE_PRESETS: dict[str, dict] = {
    "viral_yellow": {
        "text_color": "#FFE600",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "font_size": 96,
        "uppercase": True,
    },
    "tiktok_cyan": {
        "text_color": "#00F2FE",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "font_size": 96,
        "uppercase": True,
    },
    "classic_white": {
        "text_color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "font_size": 92,
        "uppercase": True,
    },
    "alert_red": {
        "text_color": "#FF2A2A",
        "stroke_color": "#FFFFFF",
        "stroke_width": 3,
        "font_size": 96,
        "uppercase": True,
    },
}

SUPPORTED_CONTAINER_FORMATS = ("mp4", "mov", "mkv")


def get_subtitle_style_preset(preset_name: str = "viral_yellow") -> dict:
    """Retrieves typography style configurations for captions by preset name."""
    return SUBTITLE_STYLE_PRESETS.get(preset_name, SUBTITLE_STYLE_PRESETS["viral_yellow"])


def find_system_font() -> str | None:
    """Finds best available impact or bold system font for high retention shorts."""
    candidate_paths = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return None


SYSTEM_FONT_PATH = find_system_font()


def validate_environment() -> dict[str, bool]:
    """Validates presence of required third-party API keys."""
    return {
        "gemini_configured": bool(GEMINI_API_KEY),
        "pixabay_configured": bool(PIXABAY_API_KEY),
    }

