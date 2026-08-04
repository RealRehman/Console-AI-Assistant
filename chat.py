from groq import Groq

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS,
)

client = Groq(api_key=GROQ_API_KEY)


def get_ai_response(messages):

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )

    return response.choices[0].message.content