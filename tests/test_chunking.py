import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from rag.chunking import chunk_segments, chunk_text


class TestChunkText(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        chunks = chunk_text("This is a short sentence. Another one.", chunk_size=180, overlap=40)
        self.assertEqual(len(chunks), 1)

    def test_long_text_is_split(self):
        text = " ".join(f"word{i}." for i in range(400))
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.split()), 100 + 20)  # a little slack for sentence boundaries

    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   "), [])

    def test_overlap_repeats_words_between_chunks(self):
        text = " ".join(f"w{i}." for i in range(300))
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        self.assertGreaterEqual(len(chunks), 2)
        tail_of_first = chunks[0].split()[-5:]
        head_of_second = chunks[1].split()[:20]
        self.assertTrue(any(w in head_of_second for w in tail_of_first))


class TestChunkSegments(unittest.TestCase):
    def test_preserves_page_metadata(self):
        segments = [
            {"text": "Content on page one. " * 5, "page": 1, "section": None},
            {"text": "Content on page two. " * 5, "page": 2, "section": None},
        ]
        chunks = chunk_segments(segments, chunk_size=180, overlap=40)
        pages = {c["page"] for c in chunks}
        self.assertEqual(pages, {1, 2})

    def test_preserves_section_metadata(self):
        segments = [
            {"text": "Intro text here.", "page": None, "section": "Introduction"},
            {"text": "Setup instructions here.", "page": None, "section": "Setup"},
        ]
        chunks = chunk_segments(segments, chunk_size=180, overlap=40)
        sections = {c["section"] for c in chunks}
        self.assertEqual(sections, {"Introduction", "Setup"})

    def test_a_chunk_never_spans_two_segments(self):
        segments = [
            {"text": "Short page one text.", "page": 1, "section": None},
            {"text": "Short page two text.", "page": 2, "section": None},
        ]
        chunks = chunk_segments(segments, chunk_size=180, overlap=40)
        for c in chunks:
            self.assertIn(c["page"], (1, 2))
            if c["page"] == 1:
                self.assertNotIn("page two", c["text"])

    def test_empty_segment_list_returns_no_chunks(self):
        self.assertEqual(chunk_segments([]), [])


if __name__ == "__main__":
    unittest.main()