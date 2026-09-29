"""
document_store.py — owns the library of uploaded documents for the
Document Q&A Assistant (Week 7).

Ingestion pipeline for every upload (Week 7.3):

    Upload -> Extract text (rag/parsers.py) -> Clean text (rag/text_cleaning.py)
           -> Chunk (rag/chunking.py) -> Generate embeddings (rag/embedder.py)
           -> Store (rag/vector_store.py, Qdrant)

Unlike the single-document version from earlier weeks, MULTIPLE
documents can be loaded at once here -- on purpose, since Week 7.6
explicitly asks you to test retrieval behavior with multiple relevant
documents, duplicate uploads, and conflicting documents.
"""

import hashlib
import uuid

from config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE, RAG_MIN_SCORE, RAG_TOP_K
from rag.chunking import chunk_segments
from rag.embedder import embed_texts
from rag.parsers import SUPPORTED_EXTENSIONS, parse_document
from rag.token_utils import count_tokens
from rag.vector_store import delete_by_doc_id, ensure_collection, search as vector_search, upsert_chunks

# doc_id -> metadata dict. Kept in-memory, same lifetime as the Flask
# process, mirroring how conversation history is stored in chat.py.
_documents = {}


def _content_hash(segments):
    joined = "\n".join(s["text"] for s in segments)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def load_document(file_path, original_filename):
    """
    Runs the full ingestion pipeline for one file and adds it to the
    library (does NOT replace previously loaded documents). Returns
    the new document's status dict. Raises ValueError on an
    unreadable, unsupported, or empty file.
    """
    ensure_collection()

    segments = parse_document(file_path)

    if not segments:
        raise ValueError(
            "No readable text was found in this file "
            "(it may be empty, scanned/image-only, or corrupted)."
        )

    content_hash = _content_hash(segments)
    duplicate_of = next(
        (doc_id for doc_id, meta in _documents.items() if meta["content_hash"] == content_hash),
        None,
    )

    chunks = chunk_segments(segments, chunk_size=RAG_CHUNK_SIZE, overlap=RAG_CHUNK_OVERLAP)
    if not chunks:
        raise ValueError("Could not split this document into chunks.")

    doc_id = str(uuid.uuid4())
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    upsert_chunks([
        {
            "text": chunk["text"],
            "vector": vector,
            "doc_id": doc_id,
            "source": original_filename,
            "page": chunk.get("page"),
            "section": chunk.get("section"),
            "chunk_index": i,
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ])

    _documents[doc_id] = {
        "doc_id": doc_id,
        "filename": original_filename,
        "chunk_count": len(chunks),
        "total_tokens": sum(count_tokens(c["text"]) for c in chunks),
        "char_count": sum(len(s["text"]) for s in segments),
        "content_hash": content_hash,
        # doc_id of an earlier upload with byte-for-byte identical
        # extracted text, if any -- surfaced so the UI/user is told
        # about it rather than silently indexing the same content twice.
        "duplicate_of": duplicate_of,
    }

    return dict(_documents[doc_id])


def get_relevant_context(query, top_k=None, doc_ids=None, min_score=None):
    """
    Returns the chunks most relevant to `query`, with citation
    metadata, across all loaded documents (or a filtered subset via
    `doc_ids`). Empty list if nothing is loaded, or if nothing scores
    above `min_score` (default RAG_MIN_SCORE) -- i.e. the question
    isn't actually covered by any loaded document.
    """
    if not _documents:
        return []

    threshold = RAG_MIN_SCORE if min_score is None else min_score
    query_vector = embed_texts([query])[0]
    matches = vector_search(query_vector, top_k=top_k or RAG_TOP_K, doc_ids=doc_ids)
    return [m for m in matches if m["score"] >= threshold]


def list_documents():
    return list(_documents.values())


def get_document_status():
    """Everything the frontend needs to show the document library panel."""
    docs = list_documents()
    return {
        "loaded": len(docs) > 0,
        "documents": docs,
        "document_count": len(docs),
        "total_chunks": sum(d["chunk_count"] for d in docs),
        "total_tokens": sum(d["total_tokens"] for d in docs),
        "chunk_size": RAG_CHUNK_SIZE,
        "chunk_overlap": RAG_CHUNK_OVERLAP,
        "top_k": RAG_TOP_K,
    }


def remove_document(doc_id):
    if doc_id not in _documents:
        raise ValueError("No document with that id is loaded.")
    delete_by_doc_id(doc_id)
    del _documents[doc_id]


def clear_all_documents():
    for doc_id in list(_documents.keys()):
        delete_by_doc_id(doc_id)
    _documents.clear()