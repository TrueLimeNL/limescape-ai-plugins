"""Google Tag Manager configuration API with platform-resolved OAuth credentials."""

from typing import Any

from limescape_plugin_sdk import NodeContext, NodeInput, NodeInputError
from limescape_plugin_sdk.errors import CapabilityError

from .helper import ACTIONS, BASE_URL, CREDENTIAL_TYPE, make_request

_ARGUMENTS = (
    "account_id",
    "container_id",
    "workspace_id",
    "tag_id",
    "trigger_id",
    "variable_id",
    "version_id",
    "body",
    "name",
    "notes",
    "fingerprint",
    "page_token",
)


async def execute(ctx: NodeContext, inp: NodeInput):
    selected_action = inp.param("action", "from_input")
    raw_action = inp.input_data.get("action", "") if selected_action == "from_input" else selected_action
    action = raw_action.strip() if isinstance(raw_action, str) else ""
    if action not in ACTIONS:
        yield {
            inp.output_key: {
                "action": action,
                "error": "Select a supported GTM action or supply input_data.action",
                "valid_actions": list(ACTIONS),
            }
        }
        return
    try:
        mode = inp.param("credential_mode", "team")
        if not isinstance(mode, str):
            raise NodeInputError("Select a valid credential mode")
        field = {
            "personal": "personal_credential_code",
            "team": "team_credential_code",
            "personal_type": "credential_type",
        }.get(mode)
        if field is None:
            raise NodeInputError("Select a valid credential mode")
        reference = inp.param(field, CREDENTIAL_TYPE if mode == "personal_type" else "")
        if not isinstance(reference, str) or not reference.strip():
            raise NodeInputError("Select a credential for the configured mode")
        if mode == "personal_type" and reference != CREDENTIAL_TYPE:
            raise NodeInputError("Select the Google Tag Manager OAuth2 credential type")
        credential = await ctx.credentials.resolve(
            reference.strip(),
            mode=mode,
            expected_type=CREDENTIAL_TYPE,
            oauth2=True,
        )
        if credential.type_name != CREDENTIAL_TYPE:
            raise NodeInputError("Selected credential is not a Google Tag Manager OAuth2 credential")
        token = credential.values.get("accessToken")
        if not isinstance(token, str) or not token.strip():
            raise NodeInputError("Selected credential has no usable OAuth access token")
        arguments: dict[str, Any] = {key: inp.params[key] for key in _ARGUMENTS if key in inp.params}
        for key in _ARGUMENTS:
            if key in inp.input_data and inp.input_data[key] is not None and inp.input_data[key] != "":
                arguments[key] = inp.input_data[key]
        request = make_request(action, arguments, credential.values)
        timeout = inp.param("request_timeout_seconds", 30)
        if isinstance(timeout, bool):
            raise NodeInputError("Request timeout must be between 1 and 120 seconds")
        try:
            timeout = float(timeout)
        except (ValueError, TypeError) as exc:
            raise NodeInputError("Request timeout must be between 1 and 120 seconds") from exc
        if not 1 <= timeout <= 120:
            raise NodeInputError("Request timeout must be between 1 and 120 seconds")
        kwargs: dict[str, Any] = {
            "headers": {"Authorization": f"Bearer {token}"},
            "params": request.query,
            "timeout": timeout,
        }
        if request.body is not None:
            kwargs["json"] = request.body
        response = await ctx.http.request(request.method, BASE_URL + request.path, **kwargs)
        ctx.trace.event("gtm_request", {"action": action, "status": response.status})
        if not 200 <= response.status < 300:
            raise NodeInputError(f"GTM API error {response.status}; check permissions, inputs and quota")
        if request.deleted:
            result: Any = {"deleted": request.path}
        else:
            try:
                result = response.json() if response.body else {}
            except ValueError as exc:
                raise NodeInputError("GTM API returned invalid JSON") from exc
        yield {inp.output_key: {"action": action, "result": result}}
    except NodeInputError as exc:
        yield {inp.output_key: {"action": action, "error": str(exc)}}
    except CapabilityError as exc:
        # Credential/provider exceptions can contain secrets; never copy their message.
        code = (
            exc.code
            if exc.code
            in {
                "not_found",
                "no_scope",
                "not_granted",
                "unsupported",
                "timeout",
                "invalid_identity",
                "ambiguous",
                "wrong_type",
                "oauth_failed",
            }
            else "failed"
        )
        yield {inp.output_key: {"action": action, "error": f"GTM capability request failed ({code})"}}
