"""Unit tests for utility functions in src.shorts_generator.utils."""

import unittest
import os
import tempfile

from src.shorts_generator.utils import (
    slugify_text,
    srt_to_vtt,
    parse_subtitles,
    split_cue_into_shorts_chunks,
    clean_subtitle_text,
    estimate_narration_duration,
)



class TestUtils(unittest.TestCase):
    def test_slugify_turkish_characters(self):
        input_text = "Çay, Kahve ve Şeker İle Öğle Yemeği"
        slug = slugify_text(input_text)
        self.assertEqual(slug, "cay-kahve-ve-seker-ile-ogle-yemegi")

    def test_slugify_punctuation_and_limits(self):
        input_text = "How AI Works?! (2026 Edition) #Shorts"
        slug = slugify_text(input_text)
        self.assertTrue(slug.startswith("how-ai-works-2026-edition-shorts"))
        self.assertLessEqual(len(slug), 45)

    def test_slugify_empty_string(self):
        slug = slugify_text("")
        self.assertEqual(slug, "shorts")

    def test_srt_to_vtt_conversion(self):
        srt = "1\n00:00:01,500 --> 00:00:03,800\nHello World\n"
        vtt = srt_to_vtt(srt)
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:01.500 --> 00:00:03.800", vtt)

    def test_split_cue_into_shorts_chunks_short_text(self):
        cues = split_cue_into_shorts_chunks(0.0, 2.0, "Hello World", max_words=2)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0], (0.0, 2.0, "Hello World"))

    def test_split_cue_into_shorts_chunks_long_text(self):
        text = "The FBI knows you are lying right now"
        cues = split_cue_into_shorts_chunks(0.0, 4.0, text, max_words=2)
        self.assertGreater(len(cues), 1)
        # Check that all chunks have at most 2 words
        for start, end, chunk in cues:
            words = chunk.split()
            self.assertLessEqual(len(words), 2)
            self.assertGreater(end, start)

        # Check total time bounds
        self.assertAlmostEqual(cues[0][0], 0.0)
        self.assertAlmostEqual(cues[-1][1], 4.0)

    def test_parse_subtitles_with_tempfile(self):
        sample_srt = (
            "1\n00:00:00,100 --> 00:00:02,500\nFirst cue sentence.\n\n"
            "2\n00:00:02,500 --> 00:00:05,000\nSecond cue line.\n"
        )
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".srt", encoding="utf-8") as f:
            f.write(sample_srt)
            temp_path = f.name

        try:
            parsed = parse_subtitles(temp_path)
            self.assertEqual(len(parsed), 2)
            self.assertAlmostEqual(parsed[0][0], 0.1)
            self.assertAlmostEqual(parsed[0][1], 2.5)
            self.assertEqual(parsed[0][2], "First cue sentence.")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_parse_subtitles_non_existent_file(self):
        parsed = parse_subtitles("non_existent_file.srt")
        self.assertEqual(parsed, [])

    def test_clean_subtitle_text_strips_markdown_and_emojis(self):
        dirty = "**ATTENTION!** [dramatic sound] You won't believe this 🔥 #viral"
        cleaned = clean_subtitle_text(dirty)
        self.assertEqual(cleaned, "ATTENTION! You won't believe this viral")

    def test_clean_subtitle_text_empty(self):
        self.assertEqual(clean_subtitle_text(""), "")

    def test_estimate_narration_duration(self):
        # 150 words per minute -> 2.5 words per second
        text_50_words = " ".join(["word"] * 50)
        duration = estimate_narration_duration(text_50_words, words_per_minute=150)
        self.assertAlmostEqual(duration, 20.0, places=1)
        self.assertEqual(estimate_narration_duration(""), 0.0)


if __name__ == "__main__":
    unittest.main()

