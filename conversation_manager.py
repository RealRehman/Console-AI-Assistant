import json
import os
from datetime import datetime

CONVERSATION_FOLDER = "conversations"

os.makedirs(CONVERSATION_FOLDER, exist_ok=True)


def create_conversation():
    """
    Creates a new conversation ID.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    conversation_id = f"chat_{timestamp}"

    return conversation_id


def save_conversation(conversation_id, messages):
    """
    Save or update a conversation.
    """

    filename = f"{conversation_id}.json"

    filepath = os.path.join(
        CONVERSATION_FOLDER,
        filename
    )

    with open(filepath, "w", encoding="utf-8") as file:

        json.dump(
            messages,
            file,
            indent=4,
            ensure_ascii=False
        )

    return filename


def list_conversations():
    """
    Returns all saved conversation files.
    """

    files = os.listdir(CONVERSATION_FOLDER)

    json_files = [
        file
        for file in files
        if file.endswith(".json")
    ]

    json_files.sort(reverse=True)

    return json_files


def load_conversation(conversation_id):
    """
    Loads a conversation using its ID.
    """

    filename = f"{conversation_id}.json"

    filepath = os.path.join(
        CONVERSATION_FOLDER,
        filename
    )

    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as file:

        messages = json.load(file)

    return messages