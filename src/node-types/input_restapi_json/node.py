"""REST override. Keep the builtin's JSON-string output and template fallbacks."""

import ast
import base64
import json
import re
from http import HTTPStatus
from typing import Any

from jinja2 import Template
from limescape_plugin_sdk import NodeContext, NodeInput
from limescape_plugin_sdk.errors import CapabilityError


def _try_parse_json_string(value: str) -> Any:
    stripped = value.strip()
    if not stripped or stripped[0] not in ("{", "["):
        return value
    try:
        return json.loads(stripped)
    except Exception:
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, (dict, list)):
                return parsed
        except (ValueError, SyntaxError, TypeError):
            return value
        return value


def _coerce_json_like_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _coerce_json_like_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_json_like_values(item) for item in value]
    if isinstance(value, str):
        parsed = _try_parse_json_string(value)
        if parsed is value:
            return value
        return _coerce_json_like_values(parsed)
    return value


def _resolve_context_path(path: str, context: dict[str, Any]) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(path)
    return current


def _build_object_from_template_variables(template: str, context: dict[str, Any]) -> dict[str, Any] | None:
    keyed_matches = re.findall(
        "[\\\"']([^\\\"']+)[\\\"']\\s*:\\s*\\{\\{\\s*([A-Za-z_][A-Za-z0-9_\\.]*)\\s*\\}\\}", template
    )
    body: dict[str, Any] = {}
    for key, path in keyed_matches:
        try:
            body[key] = _resolve_context_path(path, context)
        except KeyError:
            continue
    if body:
        return body
    matches = re.findall("\\{\\{\\s*([A-Za-z_][A-Za-z0-9_\\.]*?)\\s*\\}\\}", template)
    if not matches:
        return None
    body = {}
    for path in matches:
        key = path.split(".")[-1]
        try:
            body[key] = _resolve_context_path(path, context)
        except KeyError:
            continue
    return body if body else None


def _request_body(template: str, context: dict) -> dict | list:
    safe_context = {
        key: json.dumps(value, ensure_ascii=False)[1:-1] if isinstance(value, str) else value
        for key, value in context.items()
    }
    rendered = Template(template).render(safe_context)
    for candidate in (rendered, template):
        for parse in (json.loads, ast.literal_eval):
            try:
                result = _coerce_json_like_values(parse(candidate))
                return result if isinstance(result, (dict, list)) else {}
            except (ValueError, SyntaxError, TypeError):
                pass
    return _coerce_json_like_values(_build_object_from_template_variables(template, context) or {})


def _part(value: Any, part: Any) -> Any:
    if not part:
        return value
    if isinstance(value, list) and value:
        if isinstance(value[0], dict) and isinstance(part, str) and part in value[0]:
            return value[0][part]
        return value
    if isinstance(part, str) and isinstance(value, dict) and part in value:
        return value[part]
    if isinstance(part, str) and "." in part:
        parts = part.split(".")
    elif isinstance(part, list) and all(isinstance(key, str) for key in part):
        parts = part
    else:
        return {}
    for key in parts:
        if not isinstance(value, dict) or key not in value:
            return {}
        value = value[key]
    return value


async def _request(ctx: NodeContext, params: dict, context: dict) -> str:
    try:
        headers = {}
        auth_type = params.get("auth_type", "none")
        if auth_type == "basic":
            username = params.get("auth_username", "")
            if ":" in username:
                raise ValueError('A ":" is not allowed in login (RFC 1945#section-11.1)')
            auth_bytes = f"{username}:{params.get('auth_password', '')}".encode("latin1")
            headers["Authorization"] = "Basic " + base64.b64encode(auth_bytes).decode("ascii")
        elif auth_type == "bearer":
            headers["Authorization"] = f"Bearer {params.get('auth_token', '')}"
        elif auth_type == "custom":
            headers[params.get("auth_custom_key", "")] = params.get("auth_custom_value", "")
        url = Template(params.get("endpoint_url", "")).render(context)
        method = params.get("http_method", "GET")
        kwargs: dict[str, Any] = {"headers": headers, "params": {}}
        if method in ("POST", "PUT"):
            kwargs["json"] = _request_body(params.get("request_body_template", "{}"), context)
        response = await ctx.http.request(method, url, **kwargs)
        if response.status >= 400:
            try:
                reason = HTTPStatus(response.status).phrase
            except ValueError:
                reason = ""
            return json.dumps({"error": f"API error: {response.status} - {reason}"})
        raw = response.text
        if not raw.strip():
            value = {}
        else:
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = {"raw": raw, "status_code": response.status}
        value = _part(value, params.get("json_part", []))
        ctx.trace.event("response", {"http_method": method, "status_code": response.status})
        return json.dumps(value)
    except CapabilityError as exc:
        prefix = "Connection error" if exc.code == "request_failed" else "Unexpected error"
        return json.dumps({"error": f"{prefix}: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"Unexpected error: {exc}"})


async def execute(ctx: NodeContext, inp: NodeInput):
    params = dict(inp.params)
    reference = params.get("credential_code")
    if reference:
        credential = await ctx.credentials.get(str(reference))
        # Explicit fields only; credential values cannot overwrite endpoint/body settings.
        for field in (
            "auth_type",
            "auth_username",
            "auth_password",
            "auth_token",
            "auth_custom_key",
            "auth_custom_value",
        ):
            if field in credential.values:
                params[field] = credential.values[field]
    input_key = params.get("input_keys", "file")
    value = inp.input_data.get(input_key)
    if isinstance(value, list):
        results = []
        for item in value:
            results.append(await _request(ctx, params, {**inp.input_data, input_key: str(item)}))
        yield {inp.output_key: results}
    else:
        yield {inp.output_key: await _request(ctx, params, inp.input_data)}
