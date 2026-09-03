from groq import Groq

from document_store import get_relevant_context, get_document_status

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS,
    MODEL_CONTEXT_WINDOW,
)

from rag.token_utils import add_to_cumulative_total
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
    UI to show which document chunks were used and the running total
    of tokens used across the whole session.
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

    # Exact counts from the API for this turn
    turn_prompt_tokens = response.usage.prompt_tokens
    turn_completion_tokens = response.usage.completion_tokens
    turn_total_tokens = response.usage.total_tokens

    # Add this turn's usage to the running session total.
    # This total is only ever added to, never recomputed from scratch,
    # so it can never decrease.
    cumulative_total = add_to_cumulative_total(turn_total_tokens)

    percent_used = round((cumulative_total / MODEL_CONTEXT_WINDOW) * 100, 2)

    return {
        "response": reply,
        "used_rag": bool(matches),
        "sources": [
            {"chunk_index": m["chunk_index"], "score": m["score"]}
            for m in matches
        ],
        "token_usage": {
            "turn_prompt_tokens": turn_prompt_tokens,
            "turn_completion_tokens": turn_completion_tokens,
            "cumulative_total_tokens": cumulative_total,
            "context_window": MODEL_CONTEXT_WINDOW,
            "percent_used": percent_used,
        },
    }