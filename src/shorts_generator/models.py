"""Data structures and type schemas for AI Shorts generation pipeline."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class SubtitleCue:
    """Represents a synchronized subtitle cue."""
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        """Returns the duration of the cue in seconds."""
        return max(0.0, self.end - self.start)


@dataclass
class ScriptSegment:
    """Represents a structural section within a Shorts script (e.g., Hook, Body, CTA)."""
    section_name: str
    visual_description: str
    voiceover_text: str
    search_query: Optional[str] = None


@dataclass
class YouTubeMetadata:
    """Container for YouTube Shorts SEO metadata."""
    title: str
    description: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes metadata to standard dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YouTubeMetadata":
        """Constructs an instance from a dictionary."""
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=list(data.get("tags", [])),
        )


@dataclass
class PipelineResult:
    """Outcome and generated artifacts from an end-to-end pipeline execution."""
    topic: str
    project_dir: str
    video_path: str
    quick_output_path: str
    metadata_path: str
    metadata: Dict[str, Any]
    script: str

    def to_dict(self) -> Dict[str, Any]:
        """Converts result object to dictionary."""
        return {
            "topic": self.topic,
            "project_dir": self.project_dir,
            "video_path": self.video_path,
            "quick_output_path": self.quick_output_path,
            "metadata_path": self.metadata_path,
            "metadata": self.metadata,
            "script": self.script,
        }
