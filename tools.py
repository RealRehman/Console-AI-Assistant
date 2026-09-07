"""
Function / tool calling — Week 5.5.

Two things live here:

1. TOOLS — the JSON-schema "menu" of tools we tell the model about.
   The model never executes anything itself; it can only ask for a
   tool to be called by name with some arguments (see the diagram in
   the Week 5 notes: LLM decides -> app executes -> tool result -> LLM).

2. The actual Python implementations of those tools, plus
   execute_tool(), a small dispatcher the app calls once the model has
   asked for a specific tool.

All data here (weather, product catalog) is mock data — no external
APIs are called — which keeps the tools deterministic and free to run,
while still exercising the full tool-calling loop end-to-end.
"""

import ast
import datetime
import operator
import random

from exceptions import ToolExecutionError

# ---------------------------------------------------------------------
# 1. Tool schemas (sent to the model)
# ---------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Evaluate a basic arithmetic expression (+, -, *, /, "
                "//, %, **, parentheses) and return the numeric result. "
                "Use this for any real math instead of computing it "
                "yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A math expression, e.g. '12 * (3 + 4)'.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Bengaluru'.",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_product",
            "description": (
                "Look up a product's price, stock, and description from "
                "the store catalog by name or product id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product name or id to search for, e.g. 'keyboard' or 'P002'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


# ---------------------------------------------------------------------
# 2. Implementations
# ---------------------------------------------------------------------

# --- calculator: safe arithmetic evaluation (no eval() of arbitrary code) ---
_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](
            _eval_node(node.left), _eval_node(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported or unsafe expression.")


def calculator(expression: str) -> dict:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return {"expression": expression, "result": result}
    except ZeroDivisionError:
        return {"expression": expression, "error": "Division by zero."}
    except Exception as e:
        return {"expression": expression, "error": f"Could not evaluate expression: {e}"}


# --- weather: deterministic mock data (no live API call) ---
_WEATHER_CONDITIONS = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Clear", "Windy"]


def get_weather(city: str) -> dict:
    if not city or not city.strip():
        return {"error": "A city name is required."}

    # Seed on the city name so the same city always returns the same
    # mock reading within a run -- deterministic, but still varies by city.
    rnd = random.Random(sum(ord(c) for c in city.lower()))
    return {
        "city": city,
        "condition": rnd.choice(_WEATHER_CONDITIONS),
        "temperature_celsius": rnd.randint(10, 38),
        "humidity_percent": rnd.randint(30, 90),
        "note": "Mock weather data for demo purposes — not a live forecast.",
    }


# --- current date/time ---
def get_current_datetime() -> dict:
    now = datetime.datetime.now()
    return {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
    }


# --- product lookup: mock catalog ---
_PRODUCT_CATALOG = [
    {
        "id": "P001",
        "name": "Wireless Mouse",
        "price": 799,
        "currency": "INR",
        "in_stock": True,
        "stock_count": 42,
        "description": "Ergonomic 2.4GHz wireless mouse.",
    },
    {
        "id": "P002",
        "name": "Mechanical Keyboard",
        "price": 3499,
        "currency": "INR",
        "in_stock": True,
        "stock_count": 15,
        "description": "Hot-swappable mechanical keyboard with RGB.",
    },
    {
        "id": "P003",
        "name": "USB-C Hub",
        "price": 1299,
        "currency": "INR",
        "in_stock": False,
        "stock_count": 0,
        "description": "7-in-1 USB-C hub with HDMI and SD card reader.",
    },
    {
        "id": "P004",
        "name": "Noise Cancelling Headphones",
        "price": 5999,
        "currency": "INR",
        "in_stock": True,
        "stock_count": 8,
        "description": "Over-ear ANC headphones, 30hr battery life.",
    },
    {
        "id": "P005",
        "name": "Portable SSD 1TB",
        "price": 6999,
        "currency": "INR",
        "in_stock": True,
        "stock_count": 23,
        "description": "USB 3.2 Gen 2 portable SSD, up to 1050MB/s read.",
    },
]


def lookup_product(query: str) -> dict:
    if not query or not query.strip():
        return {"error": "A product name or id is required."}

    q = query.strip().lower()

    for product in _PRODUCT_CATALOG:
        if q == product["id"].lower() or q in product["name"].lower():
            return product

    return {
        "error": f"No product found matching '{query}'.",
        "available_products": [p["name"] for p in _PRODUCT_CATALOG],
    }


# ---------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "calculator": calculator,
    "get_weather": get_weather,
    "get_current_datetime": get_current_datetime,
    "lookup_product": lookup_product,
}


def execute_tool(name: str, arguments: dict) -> dict:
    """
    Runs the requested tool with the given arguments.

    IMPORTANT: this is the app executing the tool, not the LLM. The
    model only ever decides *which* tool to call and with what
    arguments — the actual execution (and any side effects) happen
    here, entirely under the application's control.
    """
    if name not in TOOL_FUNCTIONS:
        raise ToolExecutionError(f"Unknown tool requested: '{name}'.")

    try:
        return TOOL_FUNCTIONS[name](**(arguments or {}))
    except ToolExecutionError:
        raise
    except TypeError as e:
        raise ToolExecutionError(f"Invalid arguments for tool '{name}': {e}")
    except Exception as e:
        raise ToolExecutionError(f"Tool '{name}' failed: {e}")