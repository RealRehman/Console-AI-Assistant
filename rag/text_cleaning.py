"""
rag/text_cleaning.py — "Clean text" step of the ingestion pipeline.

Extracted text (especially from PDFs) is messy: hyphenated line
breaks, hard-wrapped lines, stray control characters, page-number-only
lines. Cleaning it first gives cleaner chunks and better embeddings.
"""

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PAGE_NUMBER_LINE = re.compile(r"^\s*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*$", re.IGNORECASE)


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub(" ", text)

    # Re-join words hyphenated across a line break: "authenti-\ncation"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if not _PAGE_NUMBER_LINE.match(ln)]

    # Keep blank lines as paragraph breaks; join hard-wrapped lines
    # inside a paragraph into a single line.
    paragraphs, current = [], []
    for ln in lines:
        if ln:
            current.append(ln)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))

    cleaned = "\n\n".join(paragraphs)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()