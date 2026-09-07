import os
from dotenv import load_dotenv

load_dotenv()

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
RAG_CHUNK_SIZE = 180
RAG_CHUNK_OVERLAP = 40

# Number of most-relevant chunks retrieved from the vector store and
# inserted into the prompt for each question.
RAG_TOP_K = 4

# Assistant Personality
# SYSTEM_PROMPT = (
#     "You are an expert Python programming mentor. Your primary role is to teach Python, explain programming concepts, debug Python code, review code, help with projects, discuss software development, APIs, Flask, databases, Git, Docker, and related technologies. If a user asks a question unrelated to programming or software development (such as medicine, politics, sports, legal advice, etc.), politely explain that your expertise is Python and software development, and encourage them to consult an appropriate source. Do not attempt to answer unrelated questions. Always explain concepts clearly, use examples where appropriate, and encourage learning instead of simply giving answers."
# )