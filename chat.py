from groq import Groq

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS
)

from system_prompt import SYSTEM_PROMPT


client = Groq(api_key=GROQ_API_KEY)


def get_ai_response(messages):

    chat_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    chat_messages.extend(messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=chat_messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_COMPLETION_TOKENS
    )

    return response.choices[0].message.content