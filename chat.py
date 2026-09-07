"""
chat.py — orchestrates a single conversation turn.

Responsibilities:
  - decide whether this turn should use RAG (a document is loaded) or
    the plain assistant system prompt
  - run the function/tool-calling loop (LLM decides -> app executes ->
    tool result -> LLM), for both non-streaming and streaming replies
  - keep the in-memory conversation history
  - track token usage for the UI's context-window bar

The actual network calls all go through llm_client.py.
"""

import json
import os
from datetime import datetime

from config import ENABLE_TOOLS, MODEL_CONTEXT_WINDOW
from conversation_manager import CONVERSATION_FOLDER
from document_store import get_document_status, get_relevant_context
from exceptions import LLMError, ToolExecutionError
from llm_client import complete, stream_complete
from logger import logger
from prompts import DOCUMENT_QA_INSTRUCTIONS, SYSTEM_PROMPT, TOOL_SYSTEM_ADDENDUM
from rag.token_utils import add_to_cumulative_total
from tools import TOOLS, execute_tool

# In-memory conversation history (excludes the system prompt, which is
# rebuilt fresh each turn since it depends on RAG matches for that turn).
# This lives for as long as the Flask process runs.
_conversation_history = []

# Path of the JSON file this running conversation is being saved to.
# Created lazily on the first saved turn, then reused for every
# subsequent turn so one chat = one file (instead of one file per turn).
_current_conversation_file = None

# Safety cap on how many tool-call <-> tool-result round trips we'll do
# for a single user message, so a confused model can't loop forever.
MAX_TOOL_ROUNDS = 3


def clear_conversation():
    """Wipes the in-memory history — call this for a 'New Chat' action."""
    _conversation_history.clear()

    global _current_conversation_file
    _current_conversation_file = None


def _persist_conversation():
    """
    Writes `_conversation_history` to disk in the conversations/ folder.

    The web app (chat_routes.py) never called conversation_manager.save_
    conversation(), so chats never made it to disk even though the
    console app's save/load flow worked fine. This mirrors that same
    save behavior for every turn, reusing one timestamped file for the
    lifetime of the in-memory history rather than creating a new file
    per message.
    """
    global _current_conversation_file

    if _current_conversation_file is None:
        os.makedirs(CONVERSATION_FOLDER, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _current_conversation_file = os.path.join(
            CONVERSATION_FOLDER, f"chat_{timestamp}.json"
        )

    try:
        with open(_current_conversation_file, "w", encoding="utf-8") as file:
            json.dump(_conversation_history, file, indent=4, ensure_ascii=False)
    except OSError as e:
        logger.error("Could not save conversation to disk: %s", e)


def _build_context_block(matches):
    parts = []
    for match in matches:
        parts.append(f"[Chunk {match['chunk_index']}] {match['text']}")
    return "\n\n".join(parts)


def _build_system_prompt(user_message):
    """Returns (system_prompt, rag_matches) for this turn."""
    status = get_document_status()
    matches = get_relevant_context(user_message) if status["loaded"] else []

    if matches:
        system_prompt = DOCUMENT_QA_INSTRUCTIONS.format(context=_build_context_block(matches))
    else:
        system_prompt = SYSTEM_PROMPT

    if ENABLE_TOOLS:
        system_prompt = f"{system_prompt}\n\n{TOOL_SYSTEM_ADDENDUM}"

    return system_prompt, matches


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
    """
    Executes a batch of tool calls (list of {id, name, arguments} dicts,
    arguments as a raw JSON string), appends the results as `tool`
    messages onto `messages`, and returns the records used for the
    frontend / logging.
    """
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
        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result),
        })

    return records


# ---------------------------------------------------------------------
# Non-streaming
# ---------------------------------------------------------------------
def get_ai_response(user_message):
    """
    Generates a reply to `user_message`, using the full conversation
    history so far as context. Automatically resolves any tool calls
    the model asks for before returning the final answer.
    """
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
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in choice.message.tool_calls
                ],
            })

            calls = [
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                for tc in choice.message.tool_calls
            ]
            tools_used.extend(_run_tool_calls(calls, messages))
            continue

        break

    reply = response.choices[0].message.content or ""

    # Now that we have the final reply, commit this turn to history so
    # the NEXT question can see it too. (Tool-call round trips are kept
    # out of the persisted history to keep it small and readable.)
    _conversation_history.append({"role": "user", "content": user_message})
    _conversation_history.append({"role": "assistant", "content": reply})
    _persist_conversation()

    usage = response.usage
    token_usage = _record_usage(usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)

    return {
        "response": reply,
        "used_rag": bool(matches),
        "sources": [{"chunk_index": m["chunk_index"], "score": m["score"]} for m in matches],
        "tools_used": tools_used,
        "token_usage": token_usage,
    }


# ---------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------
def stream_ai_response(user_message):
    """
    Generator yielding SSE-friendly event dicts for a streamed reply:

      {"type": "meta", "used_rag": bool, "sources": [...]}
      {"type": "tool_call", "name": str, "arguments": dict, "result": dict}
      {"type": "token", "content": str}
      {"type": "done", "token_usage": {...} | None}
      {"type": "error", "message": str}

    Tool calls (if any) happen *between* rounds of streamed text: the
    model streams up to the point it decides it needs a tool, we run
    the tool, feed the result back, and let it keep streaming.
    """
    try:
        system_prompt, matches = _build_system_prompt(user_message)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(_conversation_history)
        messages.append({"role": "user", "content": user_message})

        yield {
            "type": "meta",
            "used_rag": bool(matches),
            "sources": [{"chunk_index": m["chunk_index"], "score": m["score"]} for m in matches],
        }

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
                calls = [
                    {"id": c["id"], "name": c["name"], "arguments": c["arguments"]}
                    for c in round_result["tool_calls"].values()
                ]
                messages.append({
                    "role": "assistant",
                    "content": round_result["content"] or None,
                    "tool_calls": [
                        {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                        for c in calls
                    ],
                })

                for record in _run_tool_calls(calls, messages):
                    yield {"type": "tool_call", **record}

                continue

            # "final"
            usage = round_result["usage"]
            break

        _conversation_history.append({"role": "user", "content": user_message})
        _conversation_history.append({"role": "assistant", "content": full_reply})
        _persist_conversation()

        token_usage = None
        if usage:
            token_usage = _record_usage(
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                usage.get("total_tokens", 0),
            )

        yield {"type": "done", "token_usage": token_usage}

    except LLMError as e:
        logger.error("Streaming error: %s", e)
        yield {"type": "error", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected streaming error")
        yield {"type": "error", "message": "An unexpected error occurred while generating a response."}