from pathlib import Path

from limescape_plugin_sdk.errors import CapabilityError
from limescape_plugin_sdk.testing import FakeContext, run_node

NODE_DIR = Path(__file__).resolve().parents[1]


async def test_missing_configuration_has_the_builtin_error_shape(monkeypatch):
    ctx = FakeContext(granted=["websearch"])

    async def unavailable(*args, **kwargs):
        raise CapabilityError(
            "websearch", "GOOGLE_API_SERVICES_KEY environment variable is not set", code="not_configured"
        )

    monkeypatch.setattr(ctx.websearch, "search", unavailable)
    output = await run_node(NODE_DIR, ctx, params={"search_query": "hello"}, input_data={"assistant_code": "test"})
    assert output == [{"error": "GOOGLE_API_SERVICES_KEY environment variable is not set"}]
