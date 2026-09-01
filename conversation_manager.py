import json
import os
from datetime import datetime

CONVERSATION_FOLDER = "conversations"

os.makedirs(CONVERSATION_FOLDER, exist_ok=True)


def save_conversation(messages):
    """
    Save conversation to a timestamped JSON file.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{CONVERSATION_FOLDER}/chat_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(messages, file, indent=4, ensure_ascii=False)

    return filename


def list_conversations():
    """
    Returns all saved conversation files.
    """

    files = os.listdir(CONVERSATION_FOLDER)

    json_files = [
        file for file in files
        if file.endswith(".json")
    ]

    json_files.sort(reverse=True)


    return json_files


def load_conversation(filename):
    """
    Loads a conversation from a JSON file.
    """

    filepath = os.path.join(CONVERSATION_FOLDER, filename)

    with open(filepath, "r", encoding="utf-8") as file:

        messages = json.load(file)

    return messages