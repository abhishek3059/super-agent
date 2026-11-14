"""Tools the model may call. The model only names a tool; this code runs it.

Every argument comes from the model, so it is validated here, never trusted.
"""
from __future__ import annotations

import ast
import datetime
import math
import operator

TOOLS = [
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate arithmetic with numbers and + - * / // % ** and parentheses.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
]
# Gemini gets the clock too; the local adapter already has the time in its prompt.
GEMINI_FUNCTIONS = [
    {"name": "calculate", "description": TOOLS[0]["function"]["description"],
     "parameters_json_schema": TOOLS[0]["function"]["parameters"]},
    {"name": "current_time", "description": "Get the current local date and time."},
]
_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def calculate(expression: str) -> str:
    """Arithmetic only. The expression comes from the model, so it is parsed, never evaluated as code."""
    def value(node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](value(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            left, right = value(node.left), value(node.right)
            # Bounds keep a huge power from freezing the voice loop.
            if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
                raise ValueError("power too large")
            return _OPERATORS[type(node.op)](left, right)
        raise ValueError("not arithmetic")

    try:
        if not isinstance(expression, str) or len(expression) > 100:
            raise ValueError("expression too long")
        result = value(ast.parse(expression.strip(), mode="eval").body)
        # A negative number to a fractional power is complex; that is not an answer to speak.
        if type(result) not in (int, float) or not math.isfinite(result):
            raise ValueError("not a real number")
        text = f"{result:.10g}" if isinstance(result, float) else str(result)
        if len(text) > 60:
            raise ValueError("result too long to say")
        return text
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, RecursionError):
        return "error: I can only do arithmetic with numbers."


def current_time() -> str:
    """Local date and time in a form that reads well aloud."""
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")


def run_tool(name: object, arguments: object) -> str:
    """The only code a model call can reach. Unknown names and bad arguments do nothing."""
    if name == "calculate" and isinstance(arguments, dict):
        return calculate(arguments.get("expression"))
    if name == "current_time":
        return current_time()
    return "error: no such tool."
