"""Unit tests for configuration variables and validation."""

import unittest

from src.shorts_generator.config import (
    TARGET_VIDEO_WIDTH,
    TARGET_VIDEO_HEIGHT,
    DEFAULT_FPS,
    DEFAULT_BG_COUNT,
    AUDIO_DUCKING_VOLUME,
    DEFAULT_GEMINI_MODELS,
    validate_environment,
)


class TestConfig(unittest.TestCase):
    def test_dimensions_match_vertical_shorts_aspect(self):
        self.assertEqual(TARGET_VIDEO_WIDTH, 1080)
        self.assertEqual(TARGET_VIDEO_HEIGHT, 1920)
        ratio = TARGET_VIDEO_WIDTH / TARGET_VIDEO_HEIGHT
        self.assertAlmostEqual(ratio, 9 / 16, places=2)

    def test_framerate_and_audio_defaults(self):
        self.assertEqual(DEFAULT_FPS, 24)
        self.assertLessEqual(AUDIO_DUCKING_VOLUME, 0.20)
        self.assertGreater(AUDIO_DUCKING_VOLUME, 0.0)

    def test_candidate_models_exist(self):
        self.assertIsInstance(DEFAULT_GEMINI_MODELS, list)
        self.assertGreater(len(DEFAULT_GEMINI_MODELS), 0)
        self.assertTrue(any("flash" in m for m in DEFAULT_GEMINI_MODELS))

    def test_environment_validation_returns_dict(self):
        val = validate_environment()
        self.assertIn("gemini_configured", val)
        self.assertIn("pixabay_configured", val)
        self.assertIsInstance(val["gemini_configured"], bool)
        self.assertIsInstance(val["pixabay_configured"], bool)

    def test_subtitle_presets_and_lookup(self):
        from src.shorts_generator.config import SUBTITLE_STYLE_PRESETS, get_subtitle_style_preset
        self.assertIn("viral_yellow", SUBTITLE_STYLE_PRESETS)
        self.assertIn("tiktok_cyan", SUBTITLE_STYLE_PRESETS)
        preset = get_subtitle_style_preset("tiktok_cyan")
        self.assertEqual(preset["text_color"], "#00F2FE")
        # Fallback to viral_yellow when unknown
        fallback = get_subtitle_style_preset("unknown_style")
        self.assertEqual(fallback["text_color"], "#FFE600")


if __name__ == "__main__":
    unittest.main()

