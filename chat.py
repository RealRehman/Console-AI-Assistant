from groq import Groq
from document_store import get_document_context, has_document

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS
)

from system_prompt import SYSTEM_PROMPT


client = Groq(api_key=GROQ_API_KEY)


def get_ai_response(messages):
    """
    messages: full conversation history so far, as a list of
    {"role": "user"/"assistant", "content": ...} dicts
    (system prompt is NOT included here, it's added below).
    """

    if has_document():

        document_text = get_document_context()

        system_content = f"""
You are a document question-answering assistant.

Answer the user's question ONLY using the information contained
in the document below.

Do NOT use your own knowledge.
Do NOT make assumptions.
Do NOT invent information.

If the answer cannot be found in the document, say:
"I couldn't find the answer in the uploaded document."

DOCUMENT:
{document_text}
"""

    else:

        system_content = SYSTEM_PROMPT

    full_messages = [
        {
            "role": "system",
            "content": system_content
        }
    ] + messages

    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_COMPLETION_TOKENS
    )

    return response.choices[0].message.content
