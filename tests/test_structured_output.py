import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

import llm_client
from exceptions import StructuredOutputError
from models import MessageAnalysis


def _fake_response(content_str):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content_str
    return response


class TestStructuredOutput(unittest.TestCase):
    def test_valid_json_is_parsed_into_model(self):
        valid = json.dumps({
            "sentiment": "negative",
            "priority": "high",
            "category": "customer_support",
            "summary": "The customer is unhappy with a late delivery.",
        })

        with patch.object(llm_client, "complete", return_value=_fake_response(valid)) as mock_complete:
            result = llm_client.get_structured_response("My order is late!", MessageAnalysis)

        self.assertIsInstance(result, MessageAnalysis)
        self.assertEqual(result.sentiment, "negative")
        self.assertEqual(result.priority, "high")
        mock_complete.assert_called_once()

    def test_malformed_json_is_retried_then_succeeds(self):
        valid = json.dumps({
            "sentiment": "neutral",
            "priority": "low",
            "category": "general_chat",
            "summary": "A neutral greeting.",
        })

        with patch.object(
            llm_client,
            "complete",
            side_effect=[_fake_response("not valid json"), _fake_response(valid)],
        ) as mock_complete:
            result = llm_client.get_structured_response("hello", MessageAnalysis)

        self.assertEqual(result.sentiment, "neutral")
        self.assertEqual(mock_complete.call_count, 2)

    def test_gives_up_after_max_attempts(self):
        with patch.object(llm_client, "complete", return_value=_fake_response("still not json")):
            with self.assertRaises(StructuredOutputError):
                llm_client.get_structured_response("hello", MessageAnalysis, max_attempts=2)

    def test_json_missing_required_field_is_rejected(self):
        incomplete = json.dumps({"sentiment": "positive"})  # missing priority/category/summary

        with patch.object(llm_client, "complete", return_value=_fake_response(incomplete)):
            with self.assertRaises(StructuredOutputError):
                llm_client.get_structured_response("hello", MessageAnalysis, max_attempts=1)


if __name__ == "__main__":
    unittest.main()