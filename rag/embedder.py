"""
rag/embedder.py — real semantic embeddings (Week 6 model, reused here).

all-MiniLM-L6-v2 (384-dim) via chromadb's bundled ONNX runtime. Runs
locally, no API key. The model file downloads once on first use.
The same function embeds document chunks AND user queries, which is
required: vectors from different models are not comparable.
"""

from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

EMBEDDING_DIMENSIONS = 384

_fn = None


def _get_fn():
    global _fn
    if _fn is None:
        _fn = ONNXMiniLM_L6_V2()
    return _fn


def embed_texts(texts):
    """Batch-embed. Returns plain Python float lists (JSON/Qdrant safe)."""
    if not texts:
        return []
    return [[float(x) for x in vec] for vec in _get_fn()(list(texts))]


def embed_text(text):
    return embed_texts([text])[0]