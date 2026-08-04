import json
import os
from datetime import datetime

CONVERSATION_FOLDER = "conversations"

os.makedirs(CONVERSATION_FOLDER, exist_ok=True)


def save_conversation(messages):


    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{CONVERSATION_FOLDER}/chat_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(messages, file, indent=4, ensure_ascii=False)

    return filename