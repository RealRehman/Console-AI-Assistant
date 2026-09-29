"""
Splits document text into smaller overlapping chunks, and (new in
Week 7) keeps each chunk tied to the page/section it came from so
answers can cite an exact location, not just a filename.
"""

import re


def _split_into_sentences(text):
    """Very small, dependency-free sentence splitter."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text, chunk_size=180, overlap=40):
    """
    Splits `text` into overlapping chunks of ~`chunk_size` words.

    Args:
        text: Plain text to chunk.
        chunk_size: Target number of words per chunk.
        overlap: Number of words repeated between consecutive chunks,
                 so context isn't lost at the boundary.

    Returns:
        List of chunk strings (never empty strings).
    """
    sentences = _split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current_words = []

    for sentence in sentences:
        sentence_words = sentence.split()

        if current_words and len(current_words) + len(sentence_words) > chunk_size:
            chunks.append(" ".join(current_words))
            current_words = current_words[-overlap:] if overlap > 0 else []

        current_words.extend(sentence_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def chunk_segments(segments, chunk_size=180, overlap=40):
    """
    Chunks a list of parsed segments (see rag/parsers.py — each a dict
    with 'text', 'page', 'section') while preserving citation metadata.

    A segment is chunked on its own rather than concatenating all
    segments together first: this guarantees a chunk never silently
    spans two PDF pages or two Markdown/DOCX sections, so the
    page/section attached to a chunk is always accurate.
    """
    chunks = []
    for segment in segments:
        pieces = chunk_text(segment["text"], chunk_size=chunk_size, overlap=overlap)
        for piece in pieces:
            chunks.append({
                "text": piece,
                "page": segment.get("page"),
                "section": segment.get("section"),
            })
    return chunks