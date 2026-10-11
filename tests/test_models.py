"""Unit tests for models dataclasses and serialization."""

import unittest

from src.shorts_generator.models import (
    SubtitleCue,
    ScriptSegment,
    YouTubeMetadata,
    PipelineResult,
)


class TestModels(unittest.TestCase):
    def test_subtitle_cue_duration(self):
        cue = SubtitleCue(start=1.25, end=3.75, text="Hello world")
        self.assertAlmostEqual(cue.duration, 2.5)

    def test_subtitle_cue_zero_duration_when_invalid(self):
        cue = SubtitleCue(start=5.0, end=3.0, text="Backwards cue")
        self.assertEqual(cue.duration, 0.0)

    def test_script_segment_creation(self):
        seg = ScriptSegment(
            section_name="hook",
            visual_description="Terminal matrix screen",
            voiceover_text="Did you know this secret?",
            search_query="terminal coding",
        )
        self.assertEqual(seg.section_name, "hook")
        self.assertEqual(seg.search_query, "terminal coding")

    def test_youtube_metadata_to_and_from_dict(self):
        raw = {
            "title": "Shocking Coding Secrets #shorts",
            "description": "Watch until the end! #shorts #viral",
            "tags": ["coding", "python", "shorts"],
        }
        meta = YouTubeMetadata.from_dict(raw)
        self.assertEqual(meta.title, raw["title"])
        self.assertEqual(meta.tags, raw["tags"])
        serialized = meta.to_dict()
        self.assertEqual(serialized, raw)

    def test_pipeline_result_dict_interface(self):
        res = PipelineResult(
            topic="Quantum Computing",
            project_dir="outputs/quantum",
            video_path="outputs/quantum/video.mp4",
            quick_output_path="final_shorts.mp4",
            metadata_path="outputs/quantum/metadata.json",
            metadata={"title": "Quantum #shorts"},
            script="Full script...",
        )
        self.assertEqual(res["topic"], "Quantum Computing")
        self.assertEqual(res["video_path"], "outputs/quantum/video.mp4")
        self.assertTrue("topic" in res)
        self.assertFalse("unknown_key" in res)
        self.assertEqual(res.get("unknown_key", "default_val"), "default_val")
        with self.assertRaises(KeyError):
            _ = res["non_existent"]

        res_dict = res.to_dict()
        self.assertIsInstance(res_dict, dict)
        self.assertEqual(res_dict["topic"], "Quantum Computing")


if __name__ == "__main__":
    unittest.main()
