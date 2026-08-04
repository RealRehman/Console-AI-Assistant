import os
from dotenv import load_dotenv

load_dotenv()

# API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# AI Model
MODEL = "llama-3.3-70b-versatile"

# Generation Settings
TEMPERATURE = 0.7
MAX_COMPLETION_TOKENS = 500

# Assistant Personality
SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer clearly and concisely."
)