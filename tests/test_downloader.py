"""Unit tests for downloader scoring and file validation functions."""

import unittest
import os
import tempfile

from src.shorts_generator.downloader import (
    score_video_hit,
    select_best_stream_info,
    is_valid_video_file,
)


class TestDownloader(unittest.TestCase):
    def test_score_video_hit_vertical_hd(self):
        hit = {
            "videos": {
                "large": {"width": 1080, "height": 1920}
            }
        }
        score = score_video_hit(hit)
        # Vertical (+15) + HD (+8) = 23
        self.assertEqual(score, 23)

    def test_score_video_hit_landscape_sd(self):
        hit = {
            "videos": {
                "large": {"width": 640, "height": 360}
            }
        }
        score = score_video_hit(hit)
        # Landscape (+0) + SD (+0) = 0
        self.assertEqual(score, 0)

    def test_select_best_stream_info(self):
        videos = {
            "large": {"url": "https://example.com/large.mp4", "width": 1080, "height": 1920, "size": 15000000},
            "medium": {"url": "https://example.com/med.mp4", "width": 720, "height": 1280, "size": 8000000},
        }
        chosen = select_best_stream_info(videos)
        self.assertIsNotNone(chosen)
        self.assertIn("url", chosen)

    def test_is_valid_video_file_non_existent(self):
        self.assertFalse(is_valid_video_file("non_existent_file.mp4"))

    def test_is_valid_video_file_small_dummy(self):
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".mp4") as f:
            f.write(b"\x00" * 50)
            tmp_path = f.name
        try:
            self.assertFalse(is_valid_video_file(tmp_path, min_size_bytes=1000))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_is_valid_video_file_valid_size(self):
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".mp4") as f:
            f.write(b"....ftypisom...." + b"\x00" * 2000)
            tmp_path = f.name
        try:
            self.assertTrue(is_valid_video_file(tmp_path, min_size_bytes=1000))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
