import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from rag.text_cleaning import clean_text
from rag.parsers import parse_markdown, parse_txt


class TestCleanText(unittest.TestCase):
    def test_rejoins_hyphenated_line_breaks(self):
        result = clean_text("This is authenti-\ncation guidance.")
        self.assertIn("authentication", result)

    def test_strips_page_number_only_lines(self):
        result = clean_text("Some real content.\n\n12\n\nMore content.")
        self.assertNotIn("\n12\n", result)

    def test_collapses_internal_whitespace(self):
        result = clean_text("Too    many     spaces")
        self.assertNotIn("    ", result)

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")


class TestParseTxt(unittest.TestCase):
    def test_parses_plain_text_file(self):
        path = "/tmp/_week7_test.txt"
        with open(path, "w") as f:
            f.write("Hello world.\nThis is a test file.")
        try:
            segments = parse_txt(path)
            self.assertEqual(len(segments), 1)
            self.assertIn("Hello world", segments[0]["text"])
            self.assertIsNone(segments[0]["page"])
        finally:
            os.remove(path)

    def test_empty_file_returns_no_segments(self):
        path = "/tmp/_week7_empty.txt"
        with open(path, "w") as f:
            f.write("   \n   ")
        try:
            self.assertEqual(parse_txt(path), [])
        finally:
            os.remove(path)


class TestParseMarkdown(unittest.TestCase):
    def test_splits_on_headings_and_tags_sections(self):
        path = "/tmp/_week7_test.md"
        with open(path, "w") as f:
            f.write("# Intro\nWelcome text.\n\n## Setup\nSetup steps here.\n")
        try:
            segments = parse_markdown(path)
            sections = [s["section"] for s in segments]
            self.assertIn("Intro", sections)
            self.assertIn("Setup", sections)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()