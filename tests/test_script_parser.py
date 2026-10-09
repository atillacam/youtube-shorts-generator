"""Unit tests for script parsing, scene query extraction, and voiceover isolation."""

import unittest

from src.shorts_generator.script_generator import (
    extract_scene_search_queries,
    extract_search_query,
    extract_voiceover,
    generate_youtube_metadata,
)


class TestScriptParser(unittest.TestCase):
    def test_extract_scene_queries_all_tags(self):
        sample_script = """
1. Hook:
- Visual: terminal code
- Voiceover: Watch this screen now.
2. Body:
- Voiceover: AI is writing code faster than engineers.
3. CTA:
- Voiceover: Subscribe for daily AI facts.

HOOK_QUERY: terminal coder hacker
BODY_QUERY: artificial intelligence server
CTA_QUERY: futuristic robot neon
"""
        queries = extract_scene_search_queries(sample_script)
        self.assertEqual(len(queries), 3)
        self.assertEqual(queries[0], "terminal coder hacker")
        self.assertEqual(queries[1], "artificial intelligence server")
        self.assertEqual(queries[2], "futuristic robot neon")

    def test_extract_scene_queries_single_legacy_tag(self):
        sample_script = """
Script text here...
SEARCH_QUERY: space cosmos
"""
        queries = extract_scene_search_queries(sample_script)
        self.assertEqual(len(queries), 3)
        self.assertEqual(queries[0], "space cosmos")
        self.assertEqual(queries[1], "space cosmos")
        self.assertEqual(queries[2], "space cosmos")

    def test_extract_scene_queries_fallback_from_topic(self):
        sample_script = "Just a script with no query tags at all."
        queries = extract_scene_search_queries(sample_script, topic="quantum computing physics")
        self.assertEqual(len(queries), 3)
        self.assertTrue(any("quantum" in q for q in queries))

    def test_extract_voiceover_cleans_visuals_and_directions(self):
        sample_script = """
- Visual: [Dramatic zoom in on a suspect's hands]
- Voiceover: The FBI knows you are lying right now.
- Visual: [Cut to digital brain scanner with glitch effect]
- Voiceover: Guilty people add too many useless details. (camera shakes)
"""
        vo = extract_voiceover(sample_script)
        self.assertNotIn("Visual", vo)
        self.assertNotIn("Dramatic zoom", vo)
        self.assertNotIn("camera shakes", vo)
        self.assertIn("The FBI knows you are lying right now", vo)
        self.assertIn("Guilty people add too many useless details", vo)

    def test_generate_youtube_metadata_fallback(self):
        metadata = generate_youtube_metadata("Coffee Secrets", "")
        self.assertIn("title", metadata)
        self.assertIn("description", metadata)
        self.assertIn("tags", metadata)
        self.assertTrue(metadata["title"].endswith("#shorts"))


if __name__ == "__main__":
    unittest.main()
