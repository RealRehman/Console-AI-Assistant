"""
A small, self-contained vector database wrapper.

Vector DB engine : chromadb (in-memory client)
Embeddings       : scikit-learn TF-IDF vectors

Why TF-IDF instead of a neural embedding model (e.g. sentence
transformers)? Neural embedding models need to download large model
weights from the internet the first time they run, which makes the
app fragile on machines with restricted or no network access. TF-IDF
runs 100% locally/offline, needs no downloads, and for a single
document's worth of chunks it does a solid job of finding the chunks
that share vocabulary with the user's question -- which is exactly
what we need here.

Chromadb still does the real "vector database" work for us: storing
vectors, computing similarity search, and returning ranked results.
We simply hand it pre-computed embeddings instead of letting it
download its own embedding model.
"""

import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer

_COLLECTION_NAME = "document_chunks"


class VectorStore:
    def __init__(self):
        self._client = chromadb.EphemeralClient()
        self._collection = None
        self._vectorizer = None
        self._chunk_count = 0

    def is_ready(self):
        return self._collection is not None and self._chunk_count > 0

    def index_chunks(self, chunks, source_name):
        """
        Replaces whatever was previously indexed with a fresh set of
        chunks, fitting a new TF-IDF vectorizer over them.
        """

        # Drop any previous collection so re-uploading a document
        # doesn't mix chunks from two different files together.
        try:
            self._client.delete_collection(_COLLECTION_NAME)
        except Exception:
            pass

        self._collection = self._client.create_collection(_COLLECTION_NAME)

        try:
            self._vectorizer = TfidfVectorizer(stop_words="english")
            embeddings = self._vectorizer.fit_transform(chunks).toarray().tolist()
        except ValueError:
            # Happens on very short/sparse documents where removing
            # English stop words leaves an empty vocabulary.
            self._vectorizer = TfidfVectorizer()
            embeddings = self._vectorizer.fit_transform(chunks).toarray().tolist()

        ids = [f"{source_name}-{i}" for i in range(len(chunks))]
        metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(chunks))]

        self._collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        self._chunk_count = len(chunks)

    def query(self, query_text, top_k=4):
        """
        Returns the `top_k` most relevant chunks for `query_text` as a
        list of dicts: {"text": ..., "score": ..., "chunk_index": ...}
        Chunks are ranked by similarity (higher score = more relevant).
        """

        if not self.is_ready():
            return []

        query_embedding = self._vectorizer.transform([query_text]).toarray().tolist()

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self._chunk_count),
        )

        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        matches = []
        for doc, distance, meta in zip(documents, distances, metadatas):
            # Chroma returns squared-L2 distance by default; convert
            # to a friendlier 0-1 "similarity" score for the UI.
            similarity = max(0.0, 1 - distance)
            matches.append({
                "text": doc,
                "score": round(similarity, 3),
                "chunk_index": meta.get("chunk_index"),
            })

        return matches

    def clear(self):
        try:
            self._client.delete_collection(_COLLECTION_NAME)
        except Exception:
            pass
        self._collection = None
        self._vectorizer = None
        self._chunk_count = 0

    @property
    def chunk_count(self):
        return self._chunk_count
