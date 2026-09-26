from pathlib import Path

from limescape_plugin_sdk.testing import FakeContext, run_node

NODE_DIR = Path(__file__).resolve().parents[1]


async def test_outputs_the_prompt_text():
    ctx = FakeContext(granted=["prompts"], prompts={"p-1": "You are helpful."})
    assert await run_node(NODE_DIR, ctx, params={"prompt_id": "p-1"}, output_key="out") == [{"out": "You are helpful."}]
    assert ctx.calls[0].request == {"prompt_id": "p-1"}


async def test_unknown_prompt_is_empty_text():
    ctx = FakeContext(granted=["prompts"])
    assert await run_node(NODE_DIR, ctx, params={"prompt_id": "nope"}, output_key="out") == [{"out": ""}]


async def test_missing_prompt_id_is_an_error():
    ctx = FakeContext(granted=["prompts"])
    assert await run_node(NODE_DIR, ctx, params={}, output_key="out") == [{"error": "prompt_id cannot be None"}]
