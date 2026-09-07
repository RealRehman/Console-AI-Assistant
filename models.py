"""
Structured-output schemas.

These define the exact JSON shape we ask the model for, and are used
to validate + convert the model's raw JSON string into a real Python
object (see llm_client.get_structured_response).
"""

from typing import Literal

from pydantic import BaseModel, Field


class MessageAnalysis(BaseModel):
    """
    Structured classification of a single chat message — the classic
    "sentiment / priority / category" example from the Week 5 material.
    """

    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Overall emotional tone of the message."
    )
    priority: Literal["low", "medium", "high"] = Field(
        description="How urgently this message likely needs a response."
    )
    category: str = Field(
        description=(
            "Short snake_case label for the topic, e.g. "
            "'customer_support', 'technical_question', 'general_chat'."
        )
    )
    summary: str = Field(
        description="One short sentence summarizing the message."
    )


class ToolCallRecord(BaseModel):
    """A single tool invocation, for logging / returning to the frontend."""

    name: str
    arguments: dict
    result: dict