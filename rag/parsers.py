"""
rag/parsers.py — "Extract text" step. Supports TXT, Markdown, PDF, DOCX.

Every parser returns a list of *segments*:
    {"text": str, "page": int | None, "section": str | None}
so that chunks can carry citation metadata (PDF -> page number,
DOCX/Markdown -> nearest heading).
"""

import os
import re

from docx import Document
from pypdf import PdfReader

from rag.text_cleaning import clean_text

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".markdown")


def _read_text_file(path):
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return ""


def parse_txt(path):
    text = clean_text(_read_text_file(path))
    return [{"text": text, "page": None, "section": None}] if text else []


def parse_markdown(path):
    """Splits on '#' headings; each section keeps its heading as metadata."""
    raw = _read_text_file(path)
    segments, heading, buffer = [], None, []

    def flush():
        body = clean_text("\n".join(buffer))
        if body:
            segments.append({"text": body, "page": None, "section": heading})

    for line in raw.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", line)
        if match:
            flush()
            buffer.clear()
            heading = match.group(1).strip("# ").strip()
        else:
            buffer.append(line)
    flush()
    return segments


def parse_pdf(path):
    reader = PdfReader(path)
    segments = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""  # one bad page shouldn't kill the whole document
        text = clean_text(raw)
        if text:
            segments.append({"text": text, "page": page_number, "section": None})
    return segments


def parse_docx(path):
    document = Document(path)
    segments, heading, buffer = [], None, []

    def flush():
        body = clean_text("\n".join(buffer))
        if body:
            segments.append({"text": body, "page": None, "section": heading})

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            buffer.append("")
            continue
        style = (paragraph.style.name or "") if paragraph.style is not None else ""
        if style.lower().startswith("heading") or style.lower() == "title":
            flush()
            buffer.clear()
            heading = text
        else:
            buffer.append(text)
    flush()
    return segments


def parse_document(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(path)
    if ext == ".docx":
        return parse_docx(path)
    if ext in (".md", ".markdown"):
        return parse_markdown(path)
    if ext == ".txt":
        return parse_txt(path)
    raise ValueError("Unsupported file type. Use PDF, DOCX, TXT or Markdown.")