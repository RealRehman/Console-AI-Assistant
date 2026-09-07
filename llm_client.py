"""
llm_client.py — the one place in the app that actually talks to the
Groq API.

Everything else (chat.py, routes) calls the functions in this module
instead of touching the Groq SDK directly. That gives us one spot to
handle:

  - configuration (model / temperature / token limit, all from config.py)
  - timeouts
  - retries with exponential backoff
  - logging of every request/attempt/failure
  - turning SDK-specific exceptions into our own exceptions.py types
  - streaming (token-by-token, with mid-stream tool-call detection)
  - structured (JSON) output, validated against a pydantic schema
"""

import json
import time

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Groq,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from config import (
    GROQ_API_KEY,
    MAX_COMPLETION_TOKENS,
    MAX_RETRIES,
    MODEL,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF_SECONDS,
    TEMPERATURE,
)
from exceptions import (
    LLMAPIError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredOutputError,
)
from logger import logger
from prompts import STRUCTURED_ANALYSIS_PROMPT
from rag.token_utils import count_message_tokens, count_tokens

# We handle retries ourselves (so behavior is logged and configurable
# from config.py), so we disable the SDK's own built-in retrying.
_client = Groq(api_key=GROQ_API_KEY, timeout=REQUEST_TIMEOUT, max_retries=0)


# ---------------------------------------------------------------------
# Low-level call with retry / timeout / logging
# ---------------------------------------------------------------------
def _call_with_retry(**kwargs):
    """
    Calls the Groq chat.completions.create endpoint, retrying on
    transient failures (timeouts, connection errors, rate limits,
    5xx) with exponential backoff. Non-retryable errors (bad request,
    auth, etc.) fail immediately.
    """
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "LLM request | model=%s stream=%s attempt=%s/%s",
                kwargs.get("model"), kwargs.get("stream", False), attempt, MAX_RETRIES,
            )
            return _client.chat.completions.create(**kwargs)

        except RateLimitError as e:
            last_exc = e
            logger.warning("Rate limited (attempt %s/%s): %s", attempt, MAX_RETRIES, e)

        except APITimeoutError as e:
            last_exc = e
            logger.warning("Request timed out (attempt %s/%s): %s", attempt, MAX_RETRIES, e)

        except APIConnectionError as e:
            last_exc = e
            logger.warning("Connection error (attempt %s/%s): %s", attempt, MAX_RETRIES, e)

        except APIStatusError as e:
            # Only 429 and 5xx are worth retrying; other 4xx (bad
            # request, auth, not found, ...) will never succeed on retry.
            if e.status_code == 429 or e.status_code >= 500:
                last_exc = e
                logger.warning("API error %s (attempt %s/%s): %s", e.status_code, attempt, MAX_RETRIES, e)
            else:
                logger.error("Non-retryable API error %s: %s", e.status_code, e)
                raise LLMAPIError(f"LLM API error ({e.status_code}): {e}") from e

        if attempt < MAX_RETRIES:
            sleep_for = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            time.sleep(sleep_for)

    logger.error("LLM request failed after %s attempts: %s", MAX_RETRIES, last_exc)

    if isinstance(last_exc, RateLimitError):
        raise LLMRateLimitError(str(last_exc)) from last_exc
    if isinstance(last_exc, APITimeoutError):
        raise LLMTimeoutError(str(last_exc)) from last_exc
    if isinstance(last_exc, APIConnectionError):
        raise LLMConnectionError(str(last_exc)) from last_exc
    raise LLMAPIError(str(last_exc)) from last_exc


def _build_kwargs(messages, tools, tool_choice, response_format, temperature, max_tokens, model, stream):
    kwargs = {
        "model": model or MODEL,
        "messages": messages,
        "temperature": TEMPERATURE if temperature is None else temperature,
        "max_completion_tokens": MAX_COMPLETION_TOKENS if max_tokens is None else max_tokens,
        "stream": stream,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    if response_format:
        kwargs["response_format"] = response_format
    return kwargs


# ---------------------------------------------------------------------
# Non-streaming completion
# ---------------------------------------------------------------------
def complete(
    messages,
    tools=None,
    tool_choice="auto",
    response_format=None,
    temperature=None,
    max_tokens=None,
    model=None,
):
    """Single non-streaming request/response round trip."""
    kwargs = _build_kwargs(messages, tools, tool_choice, response_format, temperature, max_tokens, model, stream=False)
    return _call_with_retry(**kwargs)


# ---------------------------------------------------------------------
# Streaming completion
# ---------------------------------------------------------------------
def stream_complete(
    messages,
    tools=None,
    tool_choice="auto",
    temperature=None,
    max_tokens=None,
    model=None,
):
    """
    Streams a single model turn, yielding events as they arrive:

      {"type": "token", "content": str}
          — zero or more, one per chunk of generated text

    followed by exactly one of:

      {"type": "tool_calls", "tool_calls": {index: {id, name, arguments}}, "content": str}
          — the model wants to call one or more tools before it can answer

      {"type": "final", "content": str, "usage": {prompt_tokens, completion_tokens, total_tokens}}
          — the model is done; `usage` is exact if the provider sent it,
            otherwise a rough estimate (see rag/token_utils.py).
    """
    kwargs = _build_kwargs(messages, tools, tool_choice, None, temperature, max_tokens, model, stream=True)
    stream = _call_with_retry(**kwargs)

    collected_content = ""
    tool_calls_acc = {}
    usage = None

    try:
        for chunk in stream:
            # Groq (like OpenAI) may send usage on a final chunk that
            # has no `choices` at all.
            x_groq = getattr(chunk, "x_groq", None)
            if x_groq is not None and getattr(x_groq, "usage", None):
                usage = x_groq.usage.model_dump()

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if delta and delta.content:
                collected_content += delta.content
                yield {"type": "token", "content": delta.content}

            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    entry = tool_calls_acc.setdefault(
                        tc.index, {"id": None, "name": None, "arguments": ""}
                    )
                    if tc.id:
                        entry["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            entry["name"] = tc.function.name
                        if tc.function.arguments:
                            entry["arguments"] += tc.function.arguments

    except (APIConnectionError, APITimeoutError) as e:
        logger.error("Stream interrupted: %s", e)
        raise LLMConnectionError(f"Streaming request was interrupted: {e}") from e

    if tool_calls_acc:
        yield {"type": "tool_calls", "tool_calls": tool_calls_acc, "content": collected_content}
        return

    if usage is None:
        # Provider didn't send exact usage on this chunk stream -- fall
        # back to the same rough estimate used elsewhere in the app.
        prompt_tokens = count_message_tokens(messages)
        completion_tokens = count_tokens(collected_content)
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    yield {"type": "final", "content": collected_content, "usage": usage}


# ---------------------------------------------------------------------
# Structured (JSON) output
# ---------------------------------------------------------------------
def get_structured_response(user_text: str, schema_model: type[BaseModel], max_attempts: int = 2):
    """
    Asks the model to classify/extract `user_text` into `schema_model`
    (a pydantic BaseModel), validates the result, and returns an
    instance of that model.

    If the model returns malformed JSON or JSON that doesn't match the
    schema, we feed the error back to the model and ask it to correct
    itself, up to `max_attempts` times, before giving up.
    """
    schema_json = json.dumps(schema_model.model_json_schema(), indent=2)
    system_prompt = STRUCTURED_ANALYSIS_PROMPT.format(schema=schema_json)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    last_error = None

    for attempt in range(1, max_attempts + 1):
        response = complete(
            messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""

        try:
            data = json.loads(raw)
            return schema_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning("Structured output invalid (attempt %s/%s): %s", attempt, max_attempts, e)
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": (
                    f"That response was not valid JSON matching the schema "
                    f"({e}). Return ONLY the corrected JSON object, nothing else."
                ),
            })

    logger.error("Structured output failed after %s attempts: %s", max_attempts, last_error)
    raise StructuredOutputError(f"Could not get a valid structured response: {last_error}")