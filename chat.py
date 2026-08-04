from groq import Groq

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS
)

from system_prompt import SYSTEM_PROMPT


client = Groq(api_key=GROQ_API_KEY)


def get_ai_response(user_message):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_COMPLETION_TOKENS
    )

    return response.choices[0].message.content