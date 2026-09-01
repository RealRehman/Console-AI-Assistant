from groq import Groq

from document_store import get_relevant_context, get_document_status

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS,
    MODEL_CONTEXT_WINDOW,
)

from rag.token_utils import count_message_tokens
from system_prompt import SYSTEM_PROMPT

client = Groq(api_key=GROQ_API_KEY)


DOCUMENT_QA_INSTRUCTIONS = """You are a document question-answering assistant.

Answer the user's question using ONLY the retrieved excerpts from the
uploaded document shown below. Each excerpt is labeled with its chunk
number so you can refer back to it if useful.

Do NOT use outside knowledge. Do NOT make assumptions or invent
information that isn't in the excerpts.

If the excerpts don't contain the answer, say:
"I couldn't find the answer in the uploaded document."

RETRIEVED EXCERPTS:
{context}
"""


def _build_context_block(matches):
    parts = []
    for match in matches:
        parts.append(f"[Chunk {match['chunk_index']}] {match['text']}")
    return "\n\n".join(parts)


def get_ai_response(user_message):
    """
    Generates a reply to `user_message`.

    If a document is currently loaded, this retrieves the most
    relevant chunks for the question (RAG) and answers strictly from
    them. Otherwise it falls back to the general-purpose mentor
    system prompt.

    Returns a dict with the reply text plus enough metadata for the
    UI to show which document chunks were used and how much of the
    model's context window this request consumed.
    """

    status = get_document_status()
    matches = get_relevant_context(user_message) if status["loaded"] else []

    if matches:
        system_prompt = DOCUMENT_QA_INSTRUCTIONS.format(
            context=_build_context_block(matches)
        )
    else:
        system_prompt = SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )

    reply = response.choices[0].message.content

    prompt_tokens = count_message_tokens(messages)
    percent_used = round((prompt_tokens / MODEL_CONTEXT_WINDOW) * 100, 2)

    return {
        "response": reply,
        "used_rag": bool(matches),
        "sources": [
            {"chunk_index": m["chunk_index"], "score": m["score"]}
            for m in matches
        ],
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "context_window": MODEL_CONTEXT_WINDOW,
            "percent_used": percent_used,
        },
    }
