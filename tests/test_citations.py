import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from chat import _build_context_block, _format_source_label, _sources_payload


def _match(source="Guide.pdf", page=None, section=None, text="Some text.", score=0.42, chunk_index=0, doc_id="d1"):
    return {"source": source, "page": page, "section": section, "text": text, "score": score, "chunk_index": chunk_index, "doc_id": doc_id}


class TestFormatSourceLabel(unittest.TestCase):
    def test_with_page(self):
        self.assertEqual(_format_source_label(_match(page=3)), "Guide.pdf, Page 3")

    def test_with_section(self):
        label = _format_source_label(_match(section="Reset Procedure"))
        self.assertEqual(label, 'Guide.pdf, Section "Reset Procedure"')

    def test_with_neither(self):
        self.assertEqual(_format_source_label(_match()), "Guide.pdf")

    def test_page_takes_priority_over_section(self):
        label = _format_source_label(_match(page=3, section="Reset Procedure"))
        self.assertEqual(label, "Guide.pdf, Page 3")


class TestBuildContextBlock(unittest.TestCase):
    def test_no_matches_says_so_explicitly(self):
        block = _build_context_block([])
        self.assertIn("No relevant excerpts", block)

    def test_matches_are_labeled_and_numbered(self):
        matches = [_match(text="First chunk text.", page=1), _match(text="Second chunk text.", page=2)]
        block = _build_context_block(matches)
        self.assertIn("[Excerpt 1 | Source: Guide.pdf, Page 1]", block)
        self.assertIn("[Excerpt 2 | Source: Guide.pdf, Page 2]", block)
        self.assertIn("First chunk text.", block)
        self.assertIn("Second chunk text.", block)


class TestSourcesPayload(unittest.TestCase):
    def test_includes_label_and_score_for_ui(self):
        payload = _sources_payload([_match(page=5, score=0.81)])
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["label"], "Guide.pdf, Page 5")
        self.assertEqual(payload[0]["score"], 0.81)
        self.assertEqual(payload[0]["doc_id"], "d1")


if __name__ == "__main__":
    unittest.main()