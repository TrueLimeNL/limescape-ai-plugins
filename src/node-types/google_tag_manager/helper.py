"""Pure Google Tag Manager v2 request construction; no credentials or I/O."""

import json
import re
from dataclasses import dataclass
from typing import Any

from limescape_plugin_sdk import NodeInputError

BASE_URL = "https://tagmanager.googleapis.com/tagmanager/v2/"
CREDENTIAL_TYPE = "googleTagManagerOAuth2Api"
RESOURCE_ACTIONS = {
    f"{operation}_{singular if operation != 'list' else plural}": (operation, plural, f"{singular}_id")
    for singular, plural in [("tag", "tags"), ("trigger", "triggers"), ("variable", "variables")]
    for operation in ("list", "get", "create", "update", "delete")
}
ACTIONS = tuple(
    sorted(
        {
            *RESOURCE_ACTIONS,
            "list_accounts",
            "list_containers",
            "list_workspaces",
            "list_built_in_variables",
            "list_versions",
            "get_live_version",
            "create_version",
            "publish_version",
        }
    )
)
_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: dict[str, Any]
    body: dict[str, Any] | None = None
    deleted: bool = False


def _text(value: Any, name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise NodeInputError(f"Missing or invalid {name}")
    return str(value).strip()


def make_request(action: str, arguments: dict[str, Any], defaults: dict[str, Any]) -> Request:
    """Build a single-page request, preserving the original resource response shape."""
    query: dict[str, Any] = {}

    def identifier(name: str, credential_key: str = "") -> str:
        value = arguments.get(name)
        if value is None or value == "":
            value = defaults.get(credential_key) if credential_key else None
        result = _text(value, name)
        if not _ID.fullmatch(result):
            raise NodeInputError(f"Invalid {name}: use a GTM ID, not a URL or path")
        return result

    def account() -> str:
        return "accounts/" + identifier("account_id", "accountId")

    def container() -> str:
        return account() + "/containers/" + identifier("container_id", "containerId")

    def workspace() -> str:
        return container() + "/workspaces/" + identifier("workspace_id", "workspaceId")

    def body() -> dict[str, Any]:
        value = arguments.get("body")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise NodeInputError("body must be a JSON object") from exc
        if not isinstance(value, dict):
            raise NodeInputError("body must be a JSON object")
        return dict(value)

    def fingerprint(payload: dict[str, Any] | None = None) -> None:
        value = arguments.get("fingerprint") or (payload or {}).get("fingerprint")
        if value is not None and value != "":
            query["fingerprint"] = _text(value, "fingerprint")

    if action.startswith("list_") and arguments.get("page_token"):
        query["pageToken"] = _text(arguments["page_token"], "page_token")
    if action in RESOURCE_ACTIONS:
        operation, resource, id_field = RESOURCE_ACTIONS[action]
        path = workspace() + "/" + resource
        if operation in {"get", "update", "delete"}:
            path += "/" + identifier(id_field)
        payload = body() if operation in {"create", "update"} else None
        if operation == "update":
            fingerprint(payload)
        method = {"list": "GET", "get": "GET", "create": "POST", "update": "PUT", "delete": "DELETE"}[operation]
        return Request(method, path, query, payload, operation == "delete")
    if action == "list_accounts":
        return Request("GET", "accounts", query)
    if action == "list_containers":
        return Request("GET", account() + "/containers", query)
    if action == "list_workspaces":
        return Request("GET", container() + "/workspaces", query)
    if action == "list_built_in_variables":
        return Request("GET", workspace() + "/built_in_variables", query)
    if action == "list_versions":
        return Request("GET", container() + "/version_headers", query)
    if action == "get_live_version":
        return Request("GET", container() + "/versions:live", query)
    if action == "create_version":
        payload = {"name": _text(arguments.get("name"), "name")}
        if arguments.get("notes"):
            payload["notes"] = _text(arguments["notes"], "notes")
        return Request("POST", workspace() + ":create_version", query, payload)
    if action == "publish_version":
        fingerprint()
        return Request("POST", container() + "/versions/" + identifier("version_id") + ":publish", query)
    raise NodeInputError("Unsupported GTM action")
