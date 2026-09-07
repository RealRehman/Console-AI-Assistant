"""
Custom exceptions for the LLM layer.

Wrapping the Groq/OpenAI-style SDK exceptions in our own hierarchy means
the rest of the app (routes, chat.py) only ever has to catch these,
regardless of which underlying provider/SDK raised the original error.
This also makes it trivial to map errors to sensible HTTP status codes
in the Flask routes.
"""


class LLMError(Exception):
    """Base class for all LLM-related errors."""


class LLMTimeoutError(LLMError):
    """The request to the LLM provider timed out."""


class LLMRateLimitError(LLMError):
    """The LLM provider rejected the request due to rate limiting."""


class LLMConnectionError(LLMError):
    """A network-level error occurred talking to the LLM provider."""


class LLMAPIError(LLMError):
    """The LLM provider returned an error response (4xx/5xx)."""


class StructuredOutputError(LLMError):
    """The model's response could not be parsed/validated into the
    requested structured schema, even after retrying."""


class ToolExecutionError(LLMError):
    """A tool call failed to execute (unknown tool, bad arguments, or
    the tool itself raised an error)."""