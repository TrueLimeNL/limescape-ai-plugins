import base64
from pathlib import Path

import pytest
from limescape_plugin_sdk.testing import FakeContext, run_node

NODE_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "kind,values,header,value",
    [
        (
            "basic",
            {"auth_username": "test", "auth_password": "synthetic"},
            "Authorization",
            "Basic " + base64.b64encode(b"test:synthetic").decode(),
        ),
        ("bearer", {"auth_token": "synthetic"}, "Authorization", "Bearer synthetic"),
        ("custom", {"auth_custom_key": "X-Test", "auth_custom_value": "synthetic"}, "X-Test", "synthetic"),
    ],
)
async def test_credentials_override_legacy_values_and_cannot_change_endpoint(kind, values, header, value):
    ctx = FakeContext(
        granted=["http", "credentials"],
        credentials={
            "preset": {
                "auth_type": kind,
                **values,
                "endpoint_url": "https://wrong.test",
            }
        },
        http_responses=[{"status": 200, "json": {"ok": True}}],
    )
    output = await run_node(
        NODE_DIR,
        ctx,
        params={
            "endpoint_url": "https://api.example.test",
            "credential_code": "preset",
            "auth_token": "old",
            "auth_password": "old",
            "auth_custom_value": "old",
        },
    )
    assert output == [{"output": '{"ok": true}'}]
    assert ctx.calls[0].capability == "credentials"
    assert ctx.calls[1].request["headers"][header] == value
    assert ctx.calls[1].request["url"] == "https://api.example.test"


async def test_unknown_credential_does_not_fall_back_to_inline_secret():
    ctx = FakeContext(granted=["http", "credentials"])
    output = await run_node(NODE_DIR, ctx, params={"credential_code": "missing", "auth_token": "old"})
    assert "unknown credential" in output[0]["error"]
    assert len(ctx.calls) == 1
