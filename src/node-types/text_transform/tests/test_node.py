from pathlib import Path

import pytest
from limescape_plugin_sdk.testing import FakeContext, run_node

NODE_DIR = Path(__file__).resolve().parents[1]


async def run(**params):
    return await run_node(NODE_DIR, FakeContext(granted=[]), params=params, output_key="result")


@pytest.mark.parametrize(
    "operation, expected",
    [("strip", "Hello World"), ("upper", "  HELLO WORLD "), ("lower", "  hello world "), ("title", "  Hello World ")],
)
async def test_operations(operation, expected):
    assert await run(text="  Hello World ", operation=operation) == [{"result": expected}]


async def test_default_operation_is_strip():
    assert await run(text="  x  ") == [{"result": "x"}]


async def test_find_and_replace():
    assert await run(text="a-b-c", operation="replace", find="-", replace_with="+") == [{"result": "a+b+c"}]


async def test_find_and_replace_requires_find():
    assert await run(text="a-b-c", operation="replace") == [
        {"error": "parameter 'find' is required for find and replace"}
    ]


async def test_unknown_operation_is_an_error():
    assert await run(text="x", operation="reverse") == [{"error": "unknown operation 'reverse'"}]


async def test_non_text_input_is_converted():
    assert await run(text=42, operation="strip") == [{"result": "42"}]
