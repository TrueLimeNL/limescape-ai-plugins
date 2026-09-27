# Google Tag Manager

`google_tag_manager` turns the supplied `input_code_json` script into a native
node with an editor form, Dutch/English labels and platform credentials. It calls
the GTM v2 configuration API, not Google Analytics reporting or event ingestion.
Find it under **Marketing & Analytics** (category code `marketing_analytics`).

## Credential selection

Choose one mode and a credential/type in the node editor:

| Mode | Saved parameter | Behavior |
| --- | --- | --- |
| `personal` | `personal_credential_code` | Always uses that selected personal instance, including when someone else executes the flow. The selection intentionally shares its access with flow callers. |
| `team` | `team_credential_code` | Always uses that selected active team instance. A caller's personal credential cannot shadow it. |
| `personal_type` | `credential_type` = `googleTagManagerOAuth2Api` | Looks up the caller's personal instance of this type for each run, within the execution team. |

For type mode, pass `user_id`, `user_email` or `email` in flow input. Email-valued
`user_id` is supported; numeric platform user IDs are also resolved. Email matching
ignores case and surrounding whitespace. The user must be active and a member of
the execution team. Multiple aliases must identify the same user. Missing,
unknown or conflicting identity fails; there is no fallback to a team credential.
Multiple matching personal instances (including duplicate fixed codes belonging
to different people) also fail instead of choosing one arbitrarily.

Deep Agent tools inherit identity from the runtime context, even when nested
input keys are filtered. Model arguments and injected templates cannot replace
it. Direct flow callers must supply identity through the platform's authorized
execution path. The plugin cannot supply a different team or user to the
credential capability. Input data cannot override the saved credential mode/code.

## Platform prerequisite and first use

This node needs **SDK 0.2.2 and the accompanying platform changes**, implemented
in the sibling `limescape-ai-platform` checkout. SDK 0.2.1 only has the old
team-only `get()` method. Changing the plugin form alone is insufficient.

1. Publish/install the updated SDK, deploy the platform/worker changes and run
   the platform migrations through `credentials.0026_google_tag_manager_credential_type`.
   For local development, install the sibling SDK instead of waiting for PyPI.
2. Build and activate a **new plugin bundle version** with SDK 0.2.2. The existing
   `0.1.0` release does not contain this node. The SDK version and bundle version
   are independent. SDK 0.2.2 keeps older 0.2.x bundles compatible.
3. Enable Google Tag Manager API in the Google Cloud project. Create a Google
   OAuth client and configure the callback URL shown by Limescape (use your
   local platform URL in dev). Enter its `clientId`/`clientSecret` in a GTM
   credential or matching team preset and authorize it with the intended account.
4. Create a personal credential for `personal`/`personal_type`, or a team
   credential for `team`. Select it in the node. Start with `list_accounts`.

For local development before SDK publication, run from this plugin checkout:

```sh
uv build --wheel --out-dir /tmp/limescape-sdk-dev ../limescape-ai-platform/packages/limescape-plugin-sdk
uv sync --find-links /tmp/limescape-sdk-dev
```

CI still needs the published SDK version. See the
[validation record](../../../docs/google-tag-manager-validation.md) for the checks
performed and the remaining live-account smoke test.

The new type extends `googleOAuth2Api` and requests these scopes:

- `https://www.googleapis.com/auth/tagmanager.readonly`
- `https://www.googleapis.com/auth/tagmanager.edit.containers`
- `https://www.googleapis.com/auth/tagmanager.edit.containerversions`
- `https://www.googleapis.com/auth/tagmanager.publish`

Google account/container permissions must also allow the requested action.
An existing manually created type is preserved by the migration: check its
Google parent, fields, visibility and scopes yourself. Existing grants may need
reauthorization, especially for `create_version` and `publish_version`.

The platform reads preset overlays on each execution, refreshes missing/expired
or nearly expired access tokens at Google's fixed token endpoint, and persists
rotated tokens with compare-and-swap protection. Only `accessToken` and optional
`accountId`, `containerId`, `workspaceId` reach the plugin. Refresh tokens and
client secrets remain in the platform; the node never caches credentials.

## Actions and inputs

Choose a fixed action in the editor or **Action from flow input** (`from_input`)
and supply `action`. IDs and request data are optional editor defaults; non-empty
flow inputs override them. For account/container/workspace IDs, the final fallback
is the credential's corresponding camelCase value. Use GTM IDs, not `GTM-XXXX`
public container identifiers, URLs or resource paths.

| Actions | Required data after defaults |
| --- | --- |
| `list_accounts` | None |
| `list_containers` | `account_id` |
| `list_workspaces`, `list_versions`, `get_live_version` | `account_id`, `container_id` |
| `list_tags`, `list_triggers`, `list_variables`, `list_built_in_variables` | Account, container and `workspace_id` |
| `get_tag`, `delete_tag` | Workspace IDs and `tag_id` |
| `get_trigger`, `delete_trigger` | Workspace IDs and `trigger_id` |
| `get_variable`, `delete_variable` | Workspace IDs and `variable_id` |
| `create_tag`, `create_trigger`, `create_variable` | Workspace IDs and `body` object |
| `update_tag`, `update_trigger`, `update_variable` | Workspace IDs, resource ID and `body` object |
| `create_version` | Workspace IDs and `name`; optional `notes` |
| `publish_version` | Account, container and `version_id` |

`body` accepts a JSON object or JSON object string. Update operations accept an
optional `fingerprint`, either separately or in `body`; it is sent as a query
parameter. Publishing also accepts `fingerprint`. Lists return one page; pass
`page_token` from the preceding result's `nextPageToken` to fetch another page.
`list_versions` returns version headers, matching the original script.

Writes, deletes and publication execute immediately when their action is called.
There are no automatic retries of mutations. The HTTP timeout defaults to 30
seconds, configurable from 1 to 120; the whole node has a 180-second deadline.

Example tool input for type mode (the platform binds the email):

```json
{
  "action": "list_tags",
  "account_id": "123456",
  "container_id": "789012",
  "workspace_id": "3",
  "user_email": "alice@example.test"
}
```

Output uses the configured output key (editor default `gtm`):

```json
{"gtm": {"action": "list_tags", "result": {"tag": [], "nextPageToken": "..."}}}
```

Successful deletes return `result: {"deleted": "accounts/.../tags/..."}`.
Failures return `{"gtm": {"action": "...", "error": "safe explanation"}}`.
Google error bodies and credential exceptions are not echoed. Capability error
codes distinguish `invalid_identity`, `ambiguous`, `not_found`, `wrong_type` and
`oauth_failed`. Unknown actions also include `valid_actions`.

## Implementation and validation

`node.py` orchestrates `ctx.credentials.resolve()` and `ctx.http.request()`;
`helper.py` builds pure requests. No Google client library, private platform
imports or extra dependencies are needed. No module-level credential/client cache,
hardcoded credential code or `globalKeyValues` lookup remains.

Adjacent tests cover all 23 actions, the three saved selection modes, ID/default
precedence, fingerprints, pagination, error redaction and repeated execution.
Platform tests cover SQL scoping/ambiguity, user membership, fixed personal sharing,
OAuth refresh/rotation, the host RPC method and Deep Agent identity propagation.
Tests use synthetic data; they do not modify a real GTM container.

API references: [GTM v2](https://developers.google.com/tag-platform/tag-manager/api/v2),
[update fingerprint](https://developers.google.com/tag-platform/tag-manager/api/reference/rest/v2/accounts.containers.workspaces.tags/update),
[create version](https://developers.google.com/tag-platform/tag-manager/api/reference/rest/v2/accounts.containers.workspaces/create_version),
[publish version](https://developers.google.com/tag-platform/tag-manager/api/reference/rest/v2/accounts.containers.versions/publish).
