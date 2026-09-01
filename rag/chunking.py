"""
Splits long document text into smaller overlapping chunks.

Why chunking is needed:
LLMs (and our vector search) work far better on small, focused pieces
of text than on one giant blob. Chunking breaks a document into
pieces of roughly `chunk_size` words, with a little bit of overlap
between consecutive chunks so we don't cut an idea in half at a
chunk boundary.
"""

import re


def _split_into_sentences(text):
    """Very small, dependency-free sentence splitter."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    # Split after '.', '!' or '?' followed by whitespace + capital/number.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text, chunk_size=180, overlap=40):
    """
    Splits `text` into overlapping chunks of ~`chunk_size` words.

    Args:
        text: Full document text.
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

            # Start the next chunk with the overlap tail of the previous one.
            if overlap > 0:
                current_words = current_words[-overlap:]
            else:
                current_words = []

        current_words.extend(sentence_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks
