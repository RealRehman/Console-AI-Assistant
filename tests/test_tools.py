import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from exceptions import ToolExecutionError
from tools import calculator, execute_tool, get_current_datetime, get_weather, lookup_product


class TestCalculator(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(calculator("2 + 3")["result"], 5)
        self.assertEqual(calculator("10 / 4")["result"], 2.5)
        self.assertEqual(calculator("2 ** 5")["result"], 32)
        self.assertEqual(calculator("(2 + 3) * 4")["result"], 20)

    def test_division_by_zero_is_handled(self):
        result = calculator("1 / 0")
        self.assertIn("error", result)

    def test_unsafe_expression_is_rejected(self):
        # No names/attributes/calls allowed -- only arithmetic.
        result = calculator("__import__('os').system('echo hi')")
        self.assertIn("error", result)

    def test_malformed_expression_is_handled(self):
        result = calculator("2 + ")
        self.assertIn("error", result)


class TestWeather(unittest.TestCase):
    def test_returns_expected_fields(self):
        result = get_weather("Bengaluru")
        for key in ("city", "condition", "temperature_celsius", "humidity_percent"):
            self.assertIn(key, result)

    def test_is_deterministic_per_city(self):
        self.assertEqual(get_weather("Mumbai"), get_weather("Mumbai"))

    def test_empty_city_is_rejected(self):
        result = get_weather("")
        self.assertIn("error", result)


class TestDatetime(unittest.TestCase):
    def test_returns_expected_fields(self):
        result = get_current_datetime()
        for key in ("iso", "date", "time", "weekday"):
            self.assertIn(key, result)


class TestProductLookup(unittest.TestCase):
    def test_lookup_by_name(self):
        result = lookup_product("keyboard")
        self.assertEqual(result["id"], "P002")

    def test_lookup_by_id(self):
        result = lookup_product("p001")
        self.assertEqual(result["name"], "Wireless Mouse")

    def test_unknown_product_returns_error_with_suggestions(self):
        result = lookup_product("time machine")
        self.assertIn("error", result)
        self.assertIn("available_products", result)


class TestExecuteTool(unittest.TestCase):
    def test_dispatches_to_correct_tool(self):
        result = execute_tool("calculator", {"expression": "3 * 3"})
        self.assertEqual(result["result"], 9)

    def test_unknown_tool_raises(self):
        with self.assertRaises(ToolExecutionError):
            execute_tool("does_not_exist", {})

    def test_bad_arguments_raise(self):
        with self.assertRaises(ToolExecutionError):
            execute_tool("calculator", {"not_expression": "1+1"})


if __name__ == "__main__":
    unittest.main()