"""
Tests the multi-document library, duplicate detection, and the
Week 7.6 "question not covered by any document" behavior -- all
without touching a real Qdrant instance or downloading the embedding
model: vector_store and the embedder are mocked at the document_store
boundary.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

import document_store


def _fake_embed_texts(texts):
    return [[0.1, 0.2, 0.3] for _ in texts]


class TestLoadDocument(unittest.TestCase):
    def setUp(self):
        document_store._documents.clear()
        self._patches = [
            patch("document_store.ensure_collection", return_value=None),
            patch("document_store.upsert_chunks", return_value=None),
            patch("document_store.embed_texts", side_effect=_fake_embed_texts),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        document_store._documents.clear()

    def _write_txt(self, path, content):
        with open(path, "w") as f:
            f.write(content)

    def test_loading_a_document_adds_it_to_the_library(self):
        path = "/tmp/_w7_doc1.txt"
        self._write_txt(path, "Password reset instructions go here. " * 10)
        try:
            doc = document_store.load_document(path, "guide.txt")
            self.assertEqual(doc["filename"], "guide.txt")
            self.assertGreater(doc["chunk_count"], 0)
            self.assertIsNone(doc["duplicate_of"])
            self.assertEqual(len(document_store.list_documents()), 1)
        finally:
            os.remove(path)

    def test_uploading_identical_content_is_flagged_as_duplicate(self):
        path_a, path_b = "/tmp/_w7_dup_a.txt", "/tmp/_w7_dup_b.txt"
        content = "Identical FAQ content about billing. " * 8
        self._write_txt(path_a, content)
        self._write_txt(path_b, content)
        try:
            first = document_store.load_document(path_a, "billing_v1.txt")
            second = document_store.load_document(path_b, "billing_v2.txt")

            self.assertIsNone(first["duplicate_of"])
            self.assertEqual(second["duplicate_of"], first["doc_id"])
            self.assertEqual(len(document_store.list_documents()), 2)
        finally:
            os.remove(path_a)
            os.remove(path_b)

    def test_empty_document_is_rejected(self):
        path = "/tmp/_w7_empty.txt"
        self._write_txt(path, "   \n   ")
        try:
            with self.assertRaises(ValueError):
                document_store.load_document(path, "empty.txt")
        finally:
            os.remove(path)

    def test_remove_document_updates_the_library(self):
        path = "/tmp/_w7_doc2.txt"
        self._write_txt(path, "Some content about refunds. " * 10)
        try:
            with patch("document_store.delete_by_doc_id", return_value=None) as mock_delete:
                doc = document_store.load_document(path, "refunds.txt")
                document_store.remove_document(doc["doc_id"])
                mock_delete.assert_called_once_with(doc["doc_id"])
            self.assertEqual(document_store.list_documents(), [])
        finally:
            os.remove(path)

    def test_removing_an_unknown_document_raises(self):
        with self.assertRaises(ValueError):
            document_store.remove_document("not-a-real-id")


class TestGetRelevantContext(unittest.TestCase):
    def setUp(self):
        document_store._documents.clear()
        self.addCleanup(document_store._documents.clear)

    @patch("document_store.embed_texts", side_effect=_fake_embed_texts)
    def test_returns_empty_when_no_documents_loaded(self, _mock_embed):
        self.assertEqual(document_store.get_relevant_context("anything"), [])

    @patch("document_store.embed_texts", side_effect=_fake_embed_texts)
    @patch("document_store.vector_search")
    def test_filters_out_matches_below_min_score(self, mock_search, _mock_embed):
        document_store._documents["doc-1"] = {"doc_id": "doc-1", "filename": "x.txt", "chunk_count": 1, "total_tokens": 1, "char_count": 1, "content_hash": "h", "duplicate_of": None}
        mock_search.return_value = [
            {"score": 0.9, "text": "relevant", "doc_id": "doc-1", "source": "x.txt", "page": None, "section": None, "chunk_index": 0},
            {"score": 0.05, "text": "irrelevant", "doc_id": "doc-1", "source": "x.txt", "page": None, "section": None, "chunk_index": 1},
        ]
        results = document_store.get_relevant_context("a question", min_score=0.2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "relevant")


if __name__ == "__main__":
    unittest.main()