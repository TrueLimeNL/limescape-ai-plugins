"""GTM requests, credential selection and secret-free failure behavior."""

from pathlib import Path

import pytest
from limescape_plugin_sdk.testing import FakeContext, run_node

NODE_DIR = Path(__file__).resolve().parents[1]
TYPE = "googleTagManagerOAuth2Api"
BASE = "https://tagmanager.googleapis.com/tagmanager/v2/"
WORKSPACE = "accounts/1/containers/2/workspaces/3"


def context(*, responses=None, resolver=None):
    def resolve(reference, **options):
        return {
            "reference": reference,
            "type_name": TYPE,
            "values": {"accessToken": "synthetic-token", "accountId": "1", "containerId": "2", "workspaceId": "3"},
        }

    return FakeContext(
        granted=["credentials", "http"],
        credential_resolver=resolver or resolve,
        http_responses=responses if responses is not None else [{"status": 200, "json": {"ok": True}}],
    )


async def execute(ctx, data, **params):
    return await run_node(
        NODE_DIR,
        ctx,
        params={"credential_mode": "team", "team_credential_code": "chosen-team", **params},
        input_data=data,
        output_key="gtm",
    )


@pytest.mark.parametrize(
    "action,method,path,extra",
    [
        ("list_accounts", "GET", "accounts", {}),
        ("list_containers", "GET", "accounts/1/containers", {}),
        ("list_workspaces", "GET", "accounts/1/containers/2/workspaces", {}),
        ("list_tags", "GET", WORKSPACE + "/tags", {}),
        ("get_tag", "GET", WORKSPACE + "/tags/4", {"tag_id": "4"}),
        ("create_tag", "POST", WORKSPACE + "/tags", {"body": {"name": "demo"}}),
        ("update_tag", "PUT", WORKSPACE + "/tags/4", {"tag_id": "4", "body": {"name": "demo"}}),
        ("delete_tag", "DELETE", WORKSPACE + "/tags/4", {"tag_id": "4"}),
        ("list_triggers", "GET", WORKSPACE + "/triggers", {}),
        ("get_trigger", "GET", WORKSPACE + "/triggers/4", {"trigger_id": "4"}),
        ("create_trigger", "POST", WORKSPACE + "/triggers", {"body": {"name": "demo"}}),
        ("update_trigger", "PUT", WORKSPACE + "/triggers/4", {"trigger_id": "4", "body": {"name": "demo"}}),
        ("delete_trigger", "DELETE", WORKSPACE + "/triggers/4", {"trigger_id": "4"}),
        ("list_variables", "GET", WORKSPACE + "/variables", {}),
        ("get_variable", "GET", WORKSPACE + "/variables/4", {"variable_id": "4"}),
        ("create_variable", "POST", WORKSPACE + "/variables", {"body": {"name": "demo"}}),
        ("update_variable", "PUT", WORKSPACE + "/variables/4", {"variable_id": "4", "body": {"name": "demo"}}),
        ("delete_variable", "DELETE", WORKSPACE + "/variables/4", {"variable_id": "4"}),
        ("list_built_in_variables", "GET", WORKSPACE + "/built_in_variables", {}),
        ("list_versions", "GET", "accounts/1/containers/2/version_headers", {}),
        ("get_live_version", "GET", "accounts/1/containers/2/versions:live", {}),
        ("create_version", "POST", WORKSPACE + ":create_version", {"name": "new", "notes": "demo"}),
        ("publish_version", "POST", "accounts/1/containers/2/versions/12:publish", {"version_id": "12"}),
    ],
)
async def test_all_original_actions(action, method, path, extra):
    """Each supplied operation maps to the correct Google v2 endpoint and envelope."""
    ctx = context()
    result = await execute(ctx, {"action": action, **extra})
    request = ctx.calls[-1].request
    assert request["method"] == method
    assert request["url"] == BASE + path
    assert request["headers"] == {"Authorization": "Bearer synthetic-token"}
    expected = {"deleted": path} if method == "DELETE" else {"ok": True}
    assert result == [{"gtm": {"action": action, "result": expected}}]
    if "body" in extra:
        assert request["json"] == extra["body"]
    if action == "create_version":
        assert request["json"] == {"name": "new", "notes": "demo"}


@pytest.mark.parametrize(
    "mode,field,reference",
    [
        ("personal", "personal_credential_code", "fixed-personal"),
        ("team", "team_credential_code", "fixed-team"),
        ("personal_type", "credential_type", TYPE),
    ],
)
async def test_three_modes_use_saved_configuration(mode, field, reference):
    """Flow input cannot replace the configured identity mode or selected reference."""
    ctx = context()
    await execute(
        ctx,
        {
            "action": "list_accounts",
            "credential_mode": "team",
            "team_credential_code": "attacker",
            "user_email": "caller@example.test",
        },
        credential_mode=mode,
        **{field: reference},
    )
    assert ctx.calls[0].request == {
        "reference": reference,
        "mode": mode,
        "expected_type": TYPE,
        "oauth2": True,
    }


async def test_body_fingerprint_becomes_query_parameter_without_mutation():
    """Google's concurrency fingerprint is sent in the query, not only in the body."""
    body = {"name": "demo", "fingerprint": "original"}
    ctx = context()
    await execute(ctx, {"action": "update_tag", "tag_id": "4", "body": body})
    assert ctx.calls[-1].request["params"] == {"fingerprint": "original"}
    assert body == {"name": "demo", "fingerprint": "original"}


async def test_pagination_token_and_identifier_precedence():
    """Per-call IDs override node defaults, then credential defaults; paging remains explicit."""
    ctx = context(responses=[{"status": 200, "json": {"tag": [], "nextPageToken": "next"}}])
    result = await execute(ctx, {"action": "list_tags", "workspace_id": "9", "page_token": "page"}, workspace_id="8")
    assert ctx.calls[-1].request["url"].endswith("/workspaces/9/tags")
    assert ctx.calls[-1].request["params"] == {"pageToken": "page"}
    assert result[0]["gtm"]["result"]["nextPageToken"] == "next"


@pytest.mark.parametrize(
    "data",
    [
        {"action": "create_tag", "body": []},
        {"action": "get_tag", "tag_id": "../other"},
        {"action": "get_tag"},
        {"action": "create_version"},
    ],
)
async def test_bad_arguments_never_reach_google(data):
    """Invalid resource paths and payloads fail before the API request."""
    ctx = context()
    result = await execute(ctx, data)
    assert "error" in result[0]["gtm"]
    assert not any(call.capability == "http" for call in ctx.calls)


@pytest.mark.parametrize("status", [401, 403, 409, 429, 500])
async def test_api_errors_are_safe_and_mutations_are_not_retried(status):
    """Provider error bodies can contain secrets; failures expose only a safe status."""
    ctx = context(responses=[{"status": status, "json": {"error": "synthetic-token"}}])
    result = await execute(ctx, {"action": "create_tag", "body": {"name": "demo"}})
    assert str(status) in result[0]["gtm"]["error"]
    assert "synthetic-token" not in repr((result, ctx.log.records, ctx.trace.events))
    assert len([call for call in ctx.calls if call.capability == "http"]) == 1


async def test_no_cached_credential_between_runs():
    """A shared host must retrieve fresh credentials independently for every execution."""
    for token in ["alice-token", "bob-token"]:
        ctx = context(
            resolver=lambda reference, token=token, **options: {
                "reference": reference,
                "type_name": TYPE,
                "values": {"accessToken": token},
            }
        )
        await execute(ctx, {"action": "list_accounts"}, credential_mode="personal_type", credential_type=TYPE)
        assert ctx.calls[-1].request["headers"]["Authorization"] == "Bearer " + token


async def test_unknown_action_does_not_resolve_credentials():
    """An unsupported action returns the available actions without making capability calls."""
    ctx = context()
    result = await execute(ctx, {"action": "unknown"})
    assert "error" in result[0]["gtm"]
    assert "list_accounts" in result[0]["gtm"]["valid_actions"]
    assert ctx.calls == []


@pytest.mark.parametrize(
    "credential",
    [
        {"reference": "selected", "type_name": "wrong-type", "values": {"accessToken": "synthetic-token"}},
        {"reference": "selected", "type_name": TYPE, "values": {}},
    ],
)
async def test_invalid_credential_never_reaches_http(credential):
    """Type and token validation happen before any GTM request."""
    ctx = context(resolver=lambda **kwargs: credential)
    result = await execute(ctx, {"action": "list_accounts"})
    assert "error" in result[0]["gtm"]
    assert not [call for call in ctx.calls if call.capability == "http"]


async def test_credential_failure_is_redacted():
    """Provider exceptions cannot leak refresh secrets in output or traces."""
    from limescape_plugin_sdk.errors import CapabilityError

    def denied(**kwargs):
        raise CapabilityError("credentials", "synthetic-refresh-secret", code="oauth_failed")

    ctx = context(resolver=denied)
    result = await execute(ctx, {"action": "list_accounts"})
    assert result == [{"gtm": {"action": "list_accounts", "error": "GTM capability request failed (oauth_failed)"}}]
    assert "synthetic-refresh-secret" not in repr((result, ctx.log.records, ctx.trace.events))
    assert not [call for call in ctx.calls if call.capability == "http"]


@pytest.mark.parametrize("timeout", [True, 0, 121, "invalid", float("nan")])
async def test_timeout_must_be_bounded(timeout):
    """Malformed or unbounded timeout settings fail without starting HTTP work."""
    ctx = context()
    result = await execute(ctx, {"action": "list_accounts"}, request_timeout_seconds=timeout)
    assert "error" in result[0]["gtm"]
    assert not [call for call in ctx.calls if call.capability == "http"]
