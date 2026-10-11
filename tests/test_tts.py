"""Unit tests for TTS engine voice aliases and error handling."""

import unittest
import asyncio

from src.shorts_generator.tts_engine import (
    resolve_voice_alias,
    get_available_voice_aliases,
    text_to_speech,
    POPULAR_VOICES,
)
from src.shorts_generator.config import DEFAULT_VOICE


class TestTTSEngine(unittest.TestCase):
    def test_resolve_known_alias(self):
        resolved = resolve_voice_alias("en-us-male")
        self.assertEqual(resolved, "en-US-ChristopherNeural")

    def test_resolve_turkish_alias(self):
        resolved = resolve_voice_alias("tr-male")
        self.assertEqual(resolved, "tr-TR-AhmetNeural")

    def test_resolve_full_voice_name(self):
        full_name = "en-US-GuyNeural"
        self.assertEqual(resolve_voice_alias(full_name), full_name)

    def test_resolve_empty_or_none(self):
        self.assertEqual(resolve_voice_alias(""), DEFAULT_VOICE)

    def test_get_available_voice_aliases(self):
        aliases = get_available_voice_aliases()
        self.assertIsInstance(aliases, dict)
        self.assertEqual(len(aliases), len(POPULAR_VOICES))
        self.assertIn("en-us-female", aliases)

    def test_text_to_speech_empty_raises_value_error(self):
        with self.assertRaises(ValueError):
            asyncio.run(text_to_speech("   "))


if __name__ == "__main__":
    unittest.main()
