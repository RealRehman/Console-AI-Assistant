"""
rag/vector_store.py — Qdrant-backed vector store for the Document Q&A
Assistant (Week 7).

Runs Qdrant in embedded "local mode" by default -- everything is
stored on disk under QDRANT_PATH, no Docker/server needed. Set
QDRANT_URL to point at a real Qdrant server instead; the rest of this
file is identical either way.

Unlike the single-document version from earlier weeks, this store can
hold chunks from MULTIPLE documents at once, each chunk tagged with
its own doc_id -- this is what lets Week 7.6's "multiple relevant
documents" / "duplicate document" / "conflicting documents" scenarios
actually be tested.
"""

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from config import QDRANT_COLLECTION, QDRANT_PATH, QDRANT_URL
from rag.embedder import EMBEDDING_DIMENSIONS

_client = None


def get_client():
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL) if QDRANT_URL else QdrantClient(path=QDRANT_PATH)
    return _client


def ensure_collection(recreate=False):
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    exists = QDRANT_COLLECTION in existing

    if exists and recreate:
        client.delete_collection(QDRANT_COLLECTION)
        exists = False

    if not exists:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(size=EMBEDDING_DIMENSIONS, distance=qmodels.Distance.COSINE),
        )


def upsert_chunks(chunks):
    """
    chunks: list of dicts with keys: text, vector, doc_id, source,
    page (int|None), section (str|None), chunk_index.
    Point ids are random UUIDs -- safe across process restarts, since
    an embedded/local Qdrant collection persists on disk.
    """
    client = get_client()
    points = [
        qmodels.PointStruct(
            id=str(uuid.uuid4()),
            vector=c["vector"],
            payload={
                "text": c["text"],
                "doc_id": c["doc_id"],
                "source": c["source"],
                "page": c.get("page"),
                "section": c.get("section"),
                "chunk_index": c["chunk_index"],
            },
        )
        for c in chunks
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def search(query_vector, top_k=5, doc_ids=None):
    """
    Returns the top_k closest chunks (across all loaded documents,
    unless `doc_ids` restricts the search to a subset).
    """
    client = get_client()

    query_filter = None
    if doc_ids:
        query_filter = qmodels.Filter(
            should=[qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=d)) for d in doc_ids]
        )

    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    return [
        {
            "score": round(point.score, 4),
            "text": point.payload["text"],
            "doc_id": point.payload["doc_id"],
            "source": point.payload["source"],
            "page": point.payload.get("page"),
            "section": point.payload.get("section"),
            "chunk_index": point.payload.get("chunk_index"),
        }
        for point in response.points
    ]


def delete_by_doc_id(doc_id):
    client = get_client()
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(must=[qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=doc_id))])
        ),
    )


def clear_all():
    ensure_collection(recreate=True)


def count():
    client = get_client()
    ensure_collection()
    return client.count(collection_name=QDRANT_COLLECTION, exact=True).count