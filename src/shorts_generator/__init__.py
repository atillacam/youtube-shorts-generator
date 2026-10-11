"""AI YouTube Shorts & TikTok Generator Package.

An automated, end-to-end Python pipeline that generates viral vertical videos
with LLM scriptwriting, Edge-TTS voiceovers, dynamic captions, and MoviePy composition.
"""

__version__ = "0.2.0"
__author__ = "atillacam"

from .models import SubtitleCue, ScriptSegment, YouTubeMetadata, PipelineResult

__all__ = [
    "__version__",
    "__author__",
    "SubtitleCue",
    "ScriptSegment",
    "YouTubeMetadata",
    "PipelineResult",
]

