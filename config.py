import os
from dotenv import load_dotenv

load_dotenv()


RAG_CHUNK_SIZE = 180
RAG_CHUNK_OVERLAP = 40


RAG_TOP_K = 4


RAG_CHUNK_SIZE = 180
RAG_CHUNK_OVERLAP = 40
RAG_TOP_K = 4


# API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# AI Model
# All three of these can be overridden via environment variables
# (e.g. in .env) without touching code, per the Week 5 "Configuration
# separated from code" checklist item. Defaults match the values this
# project already used.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Generation Settings
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
MAX_COMPLETION_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))

# openai/gpt-oss-120b (served via Groq) supports a 131,072 token
# context window. This is used to show a live token-usage bar in the
# UI so the user can see how close a request is to the model's limit.
MODEL_CONTEXT_WINDOW = int(os.getenv("MODEL_CONTEXT_WINDOW", "131072"))

# ---------------- Reliability: timeouts & retries ----------------
# How long (seconds) to wait for a single request to the LLM provider
# before giving up on that attempt.
REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "30"))

# How many total attempts to make for a single request (the first try
# plus retries) before surfacing an error to the user. Only transient
# failures (timeouts, connection errors, 429s, 5xx) are retried.
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# Base delay (seconds) for exponential backoff between retries:
# attempt 1 waits RETRY_BACKOFF_SECONDS, attempt 2 waits 2x that, etc.
RETRY_BACKOFF_SECONDS = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1"))

# ---------------- Function / tool calling ----------------
# Lets tool calling be switched off entirely (e.g. for a model/provider
# that doesn't support it) without touching any other code.
ENABLE_TOOLS = os.getenv("LLM_ENABLE_TOOLS", "true").strip().lower() == "true"

# ---------------- RAG (Retrieval-Augmented Generation) ----------------
# Target size (in words) of each document chunk, and how many words
# of overlap to keep between consecutive chunks so context isn't lost
# at chunk boundaries.



# RAG_CHUNK_SIZE = 180
# RAG_CHUNK_OVERLAP = 40


# RAG_TOP_K = 4


# RAG_CHUNK_SIZE = 180
# RAG_CHUNK_OVERLAP = 40
# RAG_TOP_K = 4

# Chunks scoring below this cosine similarity are dropped from the
# retrieved context entirely, rather than being handed to the model
# just because they were the "closest available" match. Without this,
# a question genuinely unrelated to any loaded document would still
# retrieve *something* (Qdrant always returns its closest points), and
# the model could end up half-answering from irrelevant text instead
# of saying it doesn't have enough information (Week 7.6).
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.2"))

# ---------------- Vector database (Qdrant) ----------------
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "document_qa_chunks")
# Leave QDRANT_URL unset to run Qdrant in embedded "local mode" (data
# stored on disk under QDRANT_PATH, no Docker/server needed). Set
# QDRANT_URL (e.g. "http://localhost:6333") to use a real Qdrant
# server instead -- rag/vector_store.py handles either transparently.
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_data")