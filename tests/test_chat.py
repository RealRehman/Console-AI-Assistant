import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

import chat


def _fake_usage(prompt_tokens=10, completion_tokens=5, total_tokens=15):
    return MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)


def _fake_plain_response(text):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].finish_reason = "stop"
    response.choices[0].message.content = text
    response.choices[0].message.tool_calls = None
    response.usage = _fake_usage()
    return response


def _fake_tool_call_response(tool_name, arguments_json, call_id="call_1"):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].finish_reason = "tool_calls"
    response.choices[0].message.content = None

    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = tool_name
    tool_call.function.arguments = arguments_json

    response.choices[0].message.tool_calls = [tool_call]
    response.usage = _fake_usage()
    return response


class TestGetAiResponse(unittest.TestCase):
    def setUp(self):
        chat.clear_conversation()
        # Keep RAG out of the picture for these tests -- they exercise
        # the plain-chat / tool-calling path, not document retrieval.
        self._doc_status_patch = patch("chat.get_document_status", return_value={"loaded": False})
        self._doc_status_patch.start()
        self.addCleanup(self._doc_status_patch.stop)

    def tearDown(self):
        chat.clear_conversation()

    def test_plain_reply_without_tools(self):
        with patch("chat.complete", return_value=_fake_plain_response("Hello there!")) as mock_complete:
            result = chat.get_ai_response("Hi")

        self.assertEqual(result["response"], "Hello there!")
        self.assertEqual(result["tools_used"], [])
        self.assertFalse(result["used_rag"])
        mock_complete.assert_called_once()

    def test_history_grows_after_a_turn(self):
        with patch("chat.complete", return_value=_fake_plain_response("Hi!")):
            chat.get_ai_response("Hello")

        self.assertEqual(len(chat._conversation_history), 2)
        self.assertEqual(chat._conversation_history[0]["role"], "user")
        self.assertEqual(chat._conversation_history[1]["role"], "assistant")

    def test_clear_conversation_empties_history(self):
        with patch("chat.complete", return_value=_fake_plain_response("Hi!")):
            chat.get_ai_response("Hello")

        chat.clear_conversation()
        self.assertEqual(chat._conversation_history, [])

    def test_tool_call_loop_executes_tool_and_returns_final_answer(self):
        tool_response = _fake_tool_call_response("calculator", '{"expression": "2 + 2"}')
        final_response = _fake_plain_response("2 + 2 is 4.")

        with patch("chat.complete", side_effect=[tool_response, final_response]) as mock_complete:
            result = chat.get_ai_response("What is 2 + 2?")

        self.assertEqual(result["response"], "2 + 2 is 4.")
        self.assertEqual(len(result["tools_used"]), 1)
        self.assertEqual(result["tools_used"][0]["name"], "calculator")
        self.assertEqual(result["tools_used"][0]["result"]["result"], 4)
        self.assertEqual(mock_complete.call_count, 2)

    def test_unknown_tool_call_is_reported_as_error_not_a_crash(self):
        tool_response = _fake_tool_call_response("not_a_real_tool", "{}")
        final_response = _fake_plain_response("Sorry, I couldn't do that.")

        with patch("chat.complete", side_effect=[tool_response, final_response]):
            result = chat.get_ai_response("Do something impossible")

        self.assertIn("error", result["tools_used"][0]["result"])


if __name__ == "__main__":
    unittest.main()