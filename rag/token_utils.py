"""
Lightweight, dependency-free token estimation.

We don't have access to the exact tokenizer used by the model on
Groq, so we can't count tokens with 100% precision without pulling
in a heavy/network-dependent tokenizer library. Instead we use the
well-known approximation that 1 token is roughly 4 characters of
English text (this is the same rule of thumb OpenAI and others
publish). It's accurate enough to show the user a meaningful,
real-time token budget in the UI.
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
    overhead for role/formatting tokens, mirroring how chat models
    are actually billed.
    """
    total = 0
    for message in messages:
        total += count_tokens(message.get("content", ""))
        total += 4  # rough per-message role/formatting overhead
    return total
