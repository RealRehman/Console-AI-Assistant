import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

import httpx
from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

import llm_client
from exceptions import LLMAPIError, LLMConnectionError, LLMRateLimitError, LLMTimeoutError


def _fake_request():
    return httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def _fake_status_error(cls, status_code):
    response = httpx.Response(status_code, request=_fake_request())
    return cls(f"error {status_code}", response=response, body=None)


class TestCompleteSuccess(unittest.TestCase):
    def test_returns_response_on_first_success(self):
        fake_response = MagicMock()
        with patch.object(llm_client._client.chat.completions, "create", return_value=fake_response) as mock_create:
            result = llm_client.complete([{"role": "user", "content": "hi"}])
        self.assertIs(result, fake_response)
        mock_create.assert_called_once()


class TestRetryBehavior(unittest.TestCase):
    def setUp(self):
        # Don't actually sleep during tests.
        self._sleep_patch = patch("llm_client.time.sleep", return_value=None)
        self._sleep_patch.start()
        self.addCleanup(self._sleep_patch.stop)

    def test_retries_then_succeeds_on_rate_limit(self):
        fake_response = MagicMock()
        rate_limit_error = _fake_status_error(RateLimitError, 429)

        with patch.object(
            llm_client._client.chat.completions,
            "create",
            side_effect=[rate_limit_error, fake_response],
        ) as mock_create:
            result = llm_client.complete([{"role": "user", "content": "hi"}])

        self.assertIs(result, fake_response)
        self.assertEqual(mock_create.call_count, 2)

    def test_raises_llm_rate_limit_error_after_exhausting_retries(self):
        rate_limit_error = _fake_status_error(RateLimitError, 429)

        with patch.object(llm_client._client.chat.completions, "create", side_effect=rate_limit_error):
            with self.assertRaises(LLMRateLimitError):
                llm_client.complete([{"role": "user", "content": "hi"}])

    def test_raises_llm_timeout_error_after_exhausting_retries(self):
        timeout_error = APITimeoutError(request=_fake_request())

        with patch.object(llm_client._client.chat.completions, "create", side_effect=timeout_error):
            with self.assertRaises(LLMTimeoutError):
                llm_client.complete([{"role": "user", "content": "hi"}])

    def test_raises_llm_connection_error_after_exhausting_retries(self):
        connection_error = APIConnectionError(request=_fake_request())

        with patch.object(llm_client._client.chat.completions, "create", side_effect=connection_error):
            with self.assertRaises(LLMConnectionError):
                llm_client.complete([{"role": "user", "content": "hi"}])

    def test_non_retryable_error_fails_immediately(self):
        bad_request_error = _fake_status_error(APIStatusError, 400)

        with patch.object(
            llm_client._client.chat.completions, "create", side_effect=bad_request_error
        ) as mock_create:
            with self.assertRaises(LLMAPIError):
                llm_client.complete([{"role": "user", "content": "hi"}])

        # Should not have retried a non-retryable 4xx error.
        mock_create.assert_called_once()


if __name__ == "__main__":
    unittest.main()