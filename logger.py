import logging
import os

# Create logs folder if it doesn't exist
os.makedirs("logs", exist_ok=True)

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)

logger = logging.getLogger("AI_Chatbot")
logger.setLevel(logging.INFO)

# Guard against duplicate handlers if this module gets imported more
# than once (e.g. Flask's debug reloader importing app.py twice).
if not logger.handlers:
    file_handler = logging.FileHandler("logs/chatbot.log")
    file_handler.setFormatter(_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(_formatter)
    logger.addHandler(console_handler)

    logger.propagate = False