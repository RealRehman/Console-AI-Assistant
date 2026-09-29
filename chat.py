"""
chat.py — orchestrates a single conversation turn.

Week 7 adds real RAG: when one or more documents are loaded, every
turn retrieves the most relevant chunks (with citation metadata),
builds an explicit SYSTEM INSTRUCTIONS / CONTEXT / RESPONSE
REQUIREMENTS prompt (prompts.DOCUMENT_QA_INSTRUCTIONS), and returns
both the model's answer AND the raw retrieved chunks as structured
"sources" -- so citations shown to the user don't depend on the model
remembering to mention them correctly.

Function/tool calling (Week 5) still runs alongside RAG: the model can
call a tool AND answer from document context in the same turn.
"""

import json

from config import ENABLE_TOOLS, MODEL_CONTEXT_WINDOW
from document_store import get_document_status, get_relevant_context
from exceptions import LLMError, ToolExecutionError
from llm_client import complete, stream_complete
from logger import logger
from prompts import DOCUMENT_QA_INSTRUCTIONS, SYSTEM_PROMPT, TOOL_SYSTEM_ADDENDUM
from rag.token_utils import add_to_cumulative_total
from tools import TOOLS, execute_tool

_conversation_history = []
MAX_TOOL_ROUNDS = 3


def clear_conversation():
    _conversation_history.clear()


def _format_source_label(match):
    """'<filename>, Page <n>' / '<filename>, Section "<name>"' / '<filename>'."""
    if match.get("page"):
        return f'{match["source"]}, Page {match["page"]}'
    if match.get("section"):
        return f'{match["source"]}, Section "{match["section"]}"'
    return match["source"]


def _build_context_block(matches):
    if not matches:
        return "No relevant excerpts were found in the uploaded document(s) for this question."

    parts = []
    for i, match in enumerate(matches, start=1):
        parts.append(f"[Excerpt {i} | Source: {_format_source_label(match)}]\n{match['text']}")
    return "\n\n---\n\n".join(parts)


def _build_system_prompt(user_message):
    """Returns (system_prompt, rag_matches) for this turn."""
    status = get_document_status()

    if status["loaded"]:
        matches = get_relevant_context(user_message)
        system_prompt = DOCUMENT_QA_INSTRUCTIONS.format(context=_build_context_block(matches))
    else:
        matches = []
        system_prompt = SYSTEM_PROMPT

    if ENABLE_TOOLS:
        system_prompt = f"{system_prompt}\n\n{TOOL_SYSTEM_ADDENDUM}"

    return system_prompt, matches


def _sources_payload(matches):
    return [
        {
            "doc_id": m["doc_id"],
            "source": m["source"],
            "page": m.get("page"),
            "section": m.get("section"),
            "chunk_index": m.get("chunk_index"),
            "score": m["score"],
            "label": _format_source_label(m),
        }
        for m in matches
    ]


def _record_usage(prompt_tokens, completion_tokens, total_tokens):
    cumulative_total = add_to_cumulative_total(total_tokens)
    percent_used = round((cumulative_total / MODEL_CONTEXT_WINDOW) * 100, 2)
    return {
        "turn_prompt_tokens": prompt_tokens,
        "turn_completion_tokens": completion_tokens,
        "cumulative_total_tokens": cumulative_total,
        "context_window": MODEL_CONTEXT_WINDOW,
        "percent_used": percent_used,
    }


def _run_tool_calls(tool_calls, messages):
    records = []
    for call in tool_calls:
        name = call["name"]
        try:
            args = json.loads(call["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}

        logger.info("Tool call requested: %s(%s)", name, args)

        try:
            result = execute_tool(name, args)
        except ToolExecutionError as e:
            result = {"error": str(e)}
            logger.error("Tool execution failed for %s: %s", name, e)

        records.append({"name": name, "arguments": args, "result": result})
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})

    return records


# ---------------------------------------------------------------------
# Non-streaming
# ---------------------------------------------------------------------
def get_ai_response(user_message):
    system_prompt, matches = _build_system_prompt(user_message)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_conversation_history)
    messages.append({"role": "user", "content": user_message})

    tools_used = []
    response = None

    for _ in range(MAX_TOOL_ROUNDS):
        response = complete(messages, tools=TOOLS if ENABLE_TOOLS else None)
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls
                ],
            })
            calls = [{"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments} for tc in choice.message.tool_calls]
            tools_used.extend(_run_tool_calls(calls, messages))
            continue

        break

    reply = response.choices[0].message.content or ""

    _conversation_history.append({"role": "user", "content": user_message})
    _conversation_history.append({"role": "assistant", "content": reply})

    usage = response.usage
    token_usage = _record_usage(usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)

    return {
        "response": reply,
        "used_rag": bool(matches),
        "sources": _sources_payload(matches),
        "tools_used": tools_used,
        "token_usage": token_usage,
    }


# ---------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------
def stream_ai_response(user_message):
    try:
        system_prompt, matches = _build_system_prompt(user_message)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(_conversation_history)
        messages.append({"role": "user", "content": user_message})

        yield {"type": "meta", "used_rag": bool(matches), "sources": _sources_payload(matches)}

        full_reply = ""
        usage = None

        for _ in range(MAX_TOOL_ROUNDS):
            round_result = None

            for event in stream_complete(messages, tools=TOOLS if ENABLE_TOOLS else None):
                if event["type"] == "token":
                    full_reply += event["content"]
                    yield {"type": "token", "content": event["content"]}
                else:
                    round_result = event

            if round_result is None:
                break

            if round_result["type"] == "tool_calls":
                calls = [{"id": c["id"], "name": c["name"], "arguments": c["arguments"]} for c in round_result["tool_calls"].values()]
                messages.append({
                    "role": "assistant",
                    "content": round_result["content"] or None,
                    "tool_calls": [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls],
                })
                for record in _run_tool_calls(calls, messages):
                    yield {"type": "tool_call", **record}
                continue

            usage = round_result["usage"]
            break

        _conversation_history.append({"role": "user", "content": user_message})
        _conversation_history.append({"role": "assistant", "content": full_reply})

        token_usage = None
        if usage:
            token_usage = _record_usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))

        yield {"type": "done", "token_usage": token_usage}

    except LLMError as e:
        logger.error("Streaming error: %s", e)
        yield {"type": "error", "message": str(e)}
    except Exception:
        logger.exception("Unexpected streaming error")
        yield {"type": "error", "message": "An unexpected error occurred while generating a response."}