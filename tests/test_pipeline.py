"""Unit tests for ShortsPipeline orchestrator with mocked generation and dry run."""

import unittest
from unittest.mock import patch
import asyncio
import tempfile
import os

from src.shorts_generator.pipeline import ShortsPipeline
from src.shorts_generator.models import PipelineResult


class TestPipeline(unittest.TestCase):
    @patch("src.shorts_generator.pipeline.generate_shorts_script")
    @patch("src.shorts_generator.pipeline.generate_youtube_metadata")
    def test_pipeline_dry_run_and_callbacks(self, mock_meta, mock_script):
        mock_script.return_value = "Hook: Test hook.\nBody: Test body.\nCTA: Test cta."
        mock_meta.return_value = {
            "title": "Test Title #shorts",
            "description": "Test description #viral",
            "tags": ["ai", "test"],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline = ShortsPipeline(output_dir_base=temp_dir)
            progress_events = []

            def on_progress(stage: str, percent: int):
                progress_events.append((stage, percent))

            result = asyncio.run(
                pipeline.run(
                    topic="AI in Healthcare",
                    dry_run=True,
                    progress_callback=on_progress,
                )
            )

            self.assertIsInstance(result, PipelineResult)
            self.assertEqual(result.topic, "AI in Healthcare")
            self.assertEqual(result["topic"], "AI in Healthcare")
            self.assertEqual(result.metadata["title"], "Test Title #shorts")
            self.assertEqual(result["metadata"]["title"], "Test Title #shorts")
            self.assertGreater(len(progress_events), 0)
            self.assertEqual(progress_events[-1][1], 100)


if __name__ == "__main__":
    unittest.main()
