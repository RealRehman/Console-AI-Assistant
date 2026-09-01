"""
Owns the currently-uploaded document: extracting its text, splitting
it into chunks, indexing those chunks in the vector store, and
answering "what's currently loaded" questions for the rest of the
app (routes, chat.py, the frontend status panel).

Only one document is kept "active" at a time -- uploading a new file
replaces the previous one, same as the original version of this
project. What's new is that instead of stuffing the *entire*
document into every prompt, we now chunk it and retrieve only the
handful of chunks relevant to each question (see rag/vector_store.py
and get_relevant_context() below).
"""

from docx import Document
from pypdf import PdfReader

from rag.chunking import chunk_text
from rag.vector_store import VectorStore
from rag.token_utils import count_tokens
from config import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_TOP_K

_vector_store = VectorStore()

_state = {
    "filename": None,
    "chunk_count": 0,
    "total_tokens": 0,
    "char_count": 0,
}


def _extract_text_from_docx(file_path):
    document = Document(file_path)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(text)
    return "\n".join(pages)


def load_document(file_path, original_filename):
    """
    Extracts text from the uploaded file (.pdf or .docx), splits it
    into overlapping chunks, and indexes those chunks in the vector
    store so they can be retrieved later.
    """

    lowered = file_path.lower()

    if lowered.endswith(".pdf"):
        text = _extract_text_from_pdf(file_path)
    elif lowered.endswith(".docx"):
        text = _extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type.")

    if not text.strip():
        raise ValueError(
            "No readable text was found in this file "
            "(it may be a scanned/image-only document)."
        )

    chunks = chunk_text(text, chunk_size=RAG_CHUNK_SIZE, overlap=RAG_CHUNK_OVERLAP)

    if not chunks:
        raise ValueError("Could not split this document into chunks.")

    _vector_store.index_chunks(chunks, source_name=original_filename)

    _state["filename"] = original_filename
    _state["chunk_count"] = len(chunks)
    _state["total_tokens"] = sum(count_tokens(c) for c in chunks)
    _state["char_count"] = len(text)


def get_relevant_context(query, top_k=None):
    """
    Returns the chunks most relevant to `query`, along with their
    similarity scores, for use as retrieved context in the prompt.
    """

    if not _vector_store.is_ready():
        return []

    return _vector_store.query(query, top_k=top_k or RAG_TOP_K)


def get_document_status():
    """Everything the frontend needs to show the document panel."""
    return {
        "loaded": _vector_store.is_ready(),
        "filename": _state["filename"],
        "chunk_count": _state["chunk_count"],
        "total_tokens": _state["total_tokens"],
        "char_count": _state["char_count"],
        "chunk_size": RAG_CHUNK_SIZE,
        "chunk_overlap": RAG_CHUNK_OVERLAP,
        "top_k": RAG_TOP_K,
    }


def clear_document():
    _vector_store.clear()
    _state["filename"] = None
    _state["chunk_count"] = 0
    _state["total_tokens"] = 0
    _state["char_count"] = 0
