"""
Lightweight, dependency-free token estimation.

We don't have access to the exact tokenizer used by the model on
Groq, so we can't count tokens with 100% precision without pulling
in a heavy/network-dependent tokenizer library. Instead we use the
well-known approximation that 1 token is roughly 4 characters of
English text (this is the same rule of thumb OpenAI and others
publish). It's accurate enough for estimating document chunk sizes
before they're ever sent to the model.
"""

CHARS_PER_TOKEN = 4


def count_tokens(text):
    """Returns an approximate token count for a piece of text."""
    if not text:
        return 0
    return max(1, round(len(text) / CHARS_PER_TOKEN))


def count_message_tokens(messages):
    """
    Approximates the token cost of a list of chat messages
    (dicts with a "content" key), including a small per-message
    overhead for role/formatting tokens.
    """
    total = 0
    for message in messages:
        total += count_tokens(message.get("content", ""))
        total += 4  # rough per-message role/formatting overhead
    return total


# --- Cumulative session token tracker ---
# Tracks total tokens actually used (prompt + completion) across every
# turn of the conversation, for as long as this process stays running.
_cumulative_total_tokens = 0


def add_to_cumulative_total(tokens_used):
    """Adds tokens_used to the running session total and returns the new total."""
    global _cumulative_total_tokens
    _cumulative_total_tokens += tokens_used
    return _cumulative_total_tokens


def get_cumulative_total():
    """Returns the running session total without modifying it."""
    return _cumulative_total_tokens