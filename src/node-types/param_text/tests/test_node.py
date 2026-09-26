from pathlib import Path

from limescape_plugin_sdk.testing import FakeContext, run_node

NODE_DIR = Path(__file__).resolve().parents[1]


async def test_outputs_the_text():
    assert await run_node(NODE_DIR, FakeContext(granted=[]), params={"text_value": "hi"}, output_key="out") == [
        {"out": "hi"}
    ]


async def test_missing_text_yields_none_like_the_builtin():
    assert await run_node(NODE_DIR, FakeContext(granted=[]), params={}, output_key="out") == [{"out": None}]
