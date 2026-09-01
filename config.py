import os
from dotenv import load_dotenv

load_dotenv()

# API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# AI Model
MODEL = "openai/gpt-oss-120b"

# Generation Settings
TEMPERATURE = 0.7
MAX_COMPLETION_TOKENS = 500

# openai/gpt-oss-120b (served via Groq) supports a 131,072 token
# context window. This is used to show a live token-usage bar in the
# UI so the user can see how close a request is to the model's limit.
MODEL_CONTEXT_WINDOW = 131072

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