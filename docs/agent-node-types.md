# Creating node types with a coding agent

This is the implementation workflow for **dynamic plugins in this repository**.
It is also the reference material for a future Claude Code skill. It is not an
installed skill and does not define new SDK capabilities.

Checked on 2026-09-27 against SDK 0.2.1 and the local `limescape-ai-platform`
checkout (HEAD `d361dc620`, with local changes). The checkout is a development
reference, not proof that the same code is deployed. Prefer actual code/config
when historical plans or examples disagree; recheck the pinned SDK and deployed
platform before depending on newer behavior.

## 1. Establish the contract before copying a node

Write down these decisions in the node's README or implementation brief:

| Decision | Required detail |
| --- | --- |
| Identity | Unique code, purpose, category; new node or deliberate builtin override |
| Inputs | Form fields, defaults, required flow inputs and variable resolution |
| Outputs | Exact JSON shape and how downstream nodes select results |
| Authentication | None/platform-owned, or the three credential modes: selected personal code, selected team code, selected type resolved for the executing user; see [credential contract](credentials-and-node-types.md) |
| Identity for type selection | Email resolution from `user_id`, `user_email` or `email`; propagation through Deep Agent tool calls and nested flow inputs |
| External calls | Destinations, timeouts, pagination, rate limits and side effects; idempotency for retried writes |
| Runtime | Capabilities, dependencies, trace mode, isolation and timeout |
| Availability | General or opt-in; platform/type/SDK prerequisites |
| Evidence | Closest existing example, compatibility baseline and test scenarios |

For nodes needing user-configured credentials, include all three selection modes
in the design and acceptance cases. In type mode, the node stores the selected
type rather than one caller's credential code. The current team-only SDK example
is not the full product contract: identify and implement required platform/SDK
support before claiming the personal modes work.

Resolve unknown credential field names and unsupported capabilities before
promising a working integration. Ask only for decisions that cannot be derived
from the repository or supplied requirements. Never ask for real secrets.

## 2. Apply platform guidelines at the right boundary

The platform's builtin node types use `tasks.py` plus `helper.py`, metadata from
`get_meta_description()` and platform tracing decorators. Dynamic plugins use a
different public entry point while preserving the same design principles:

| Platform guideline | Application in this repository |
| --- | --- |
| Thin orchestration with separate business logic | `node.py:execute(ctx, inp)` plus pure functions or relative `helper.py` modules |
| Existing form metadata shape | `form.fields` and `form.layout` in `node-type.yaml` |
| Normalize parameters and validate inputs | The platform prepares `NodeInput`; validate node-specific types, values and defaults in the plugin |
| Structured, secret-free trace checkpoints | `runtime.trace` plus `ctx.trace.event(...)`; no imports of `llm_trace` or edits to builtin trace registries |
| Dependencies belong to their component | Runtime third-party packages go in that node's manifest; repo development tools go in `pyproject.toml` |
| Small changes, tests and documentation | One node per folder; adjacent behavior tests and a user-facing README |
| Backward compatibility | This plugin repo requires compatibility even where generic platform guidance permits breaking changes |

Do not copy platform `execute(skill_io_message)`, SQL helpers, `TeamContext`,
Django models or `process_skill_parameters_and_validate_input` into the plugin.
Use platform source as a behavior reference, not an importable dependency.
This repo versions releases with a git tag; the platform's `update_version.sh`
and workspace package commands are not the plugin release procedure.

## 3. Scaffold and implement

Start with [text_transform](../src/node-types/text_transform) for a small new
node. Use [prompt_to_text](../src/node-types/prompt_to_text) for prompt lookup or
[text_to_websearch](../src/node-types/text_to_websearch) for platform-owned search.
The [REST override](../src/node-types/input_restapi_json) is useful for legacy
compatibility tests, but its inline secret fields and authentication mapping
are not a generic credential schema.

```text
src/node-types/<code>/
  node-type.yaml
  node.py
  helper.py           # optional, relative imports within this folder
  i18n/nl.json
  i18n/en.json
  README.md
  tests/test_node.py
  tests/golden/*.yaml # required for a builtin override
```

- Codes must match `^[a-z][a-z0-9_]{2,63}$`. Check the SDK's `catalog.py` for
  reserved codes and supported categories; do not invent a new category.
- Metadata lives in the manifest. Every layout field must exist; every labeled
  field needs a translation in both locales. Translation shape is `name`,
  `description`, `fields.<field_name>.label` and optional field descriptions.
- Declare every used capability and direct third-party dependency. Transitive
  installation does not count as a declaration. Dependencies must coexist with
  all nodes and have wheels for CPython 3.12 on Linux amd64/glibc.
- `execute` must be an async generator and yield JSON-serializable dicts or lists
  of dicts. Usually yield `{inp.output_key: result}`. The engine converts a raised
  exception to `[{"error": "..."}]`; exception text must be safe to expose.
- `inp.params` uses manifest field names. Stored `credentialCode` becomes
  `credential_code`; credential **values** do not undergo this normalization.
- Use `inp.param(name, default)` / `inp.require_param(name)` for actual runtime
  defaults/validation. Do not assume a manifest default is injected into every
  old stored configuration or by `run_node`.
- Variables are prepared by the platform. Use `resolve_variables: false` only
  for fields whose template processing deliberately belongs to the node.
- Keys declared in `io.input_data` are required flow input keys. Optional inputs
  should be validated by the node. Prefer default `io.input_keys_validation:
  platform`; use `plugin` only for a justified alternative-input contract.
- `runtime.manages_output_keys: false` is the usual choice. `input_keys` remains
  available in params; `output_key` is supplied separately by the platform.
- Use bounded external calls and stable trace metadata such as operation,
  counts and status codes. `ctx.log` and `ctx.trace` are synchronous calls;
  `http`, `credentials`, `prompts` and `websearch` methods are awaited.

A bundle version is pinned for an entire run. A plugin using a builtin's code
intentionally takes over that node in supported agent flows; execution failures
must not silently switch to the builtin. Team templates contain configuration,
not executable plugin code. A successful local test does not activate a bundle.

## 4. Test behavior and preserve compatibility

Use `limescape_plugin_sdk.testing.run_node` so imports and yielded values follow
the SDK loader. Set `FakeContext(granted=manifest.capabilities)` explicitly;
omitting `granted` allows every fake capability and can hide missing declarations.
`run_node` does not validate the manifest, inject defaults, resolve variables,
render the UI or contact the platform database. Run manifest validation separately.

Cover the applicable behaviors:

- Normal response, empty response and the exact output key/shape.
- Required/malformed input, defaults and documented alternative inputs.
- All three credential selection modes, persisted code/type distinctions and
  exact personal/team resolution.
- Type selection with `user_id`, `user_email` and `email` individually; preserve
  caller identity when a Deep Agent invokes the flow as a tool. Include two
  different users, ambiguous matches and no personal-to-team fallback.
- Missing credential, missing/malformed secret fields, rejected capability and
  no HTTP request after credential validation fails.
- HTTP failures, timeout, pagination termination and safe error/log/trace data.
- Credential mapping cannot overwrite unrelated endpoint/body configuration.
- Repeat execution with different credentials to catch retained global state.

Use synthetic fixtures and short test docstrings that explain the behavior.
Check errors returned by `run_node`, or set `catch_errors=False` when asserting
an exception. See the executable example in [the credential guide](credentials-and-node-types.md).
Team isolation, personal credentials, type filtering and preset rotation require
platform tests or a real development-platform smoke test; fake credentials do
not establish those properties.

For an override, use `compat/legacy/<code>.yaml` and golden cases recorded from
the builtin (platform script `scripts/plugins/record_golden.py`). Preserve field
types, stored choice values, lookup targets, input/output contract, execution
mode, output-key handling and legacy trace mode. Do not generate expected golden
outputs from the new implementation. Additive required fields need defaults;
removing/renaming/retyping fields or changing output behavior needs a new code.
Keep the old type with `stage: deprecated`. Review lookup-filter changes manually:
compatibility checks do not prove existing credential selections still work.

## 5. Validate locally

Run from this repository, using Python 3.12. These individual commands work in
Fish or Bash; the dependency script explicitly uses Bash.

```sh
uv sync
uv run --no-sync limescape-plugin validate
uv run --no-sync bash scripts/lock_dependencies.sh build
uv pip install --python .venv/bin/python --offline --no-index --no-deps --require-hashes --find-links build/wheels --requirement build/bundle.lock
uv run --no-sync limescape-plugin validate --check-imports
uv run --no-sync pytest
uv run --no-sync limescape-plugin golden
uv run --no-sync limescape-plugin compat
uv run --no-sync ruff check src
uv run --no-sync bash -c 'for folder in src/node-types/*/; do mypy "$folder" || exit; done'
uv run --no-sync bandit -q -r src -x '*/tests/*'
```

The dependency step needs `pip` available to the Python invoked by the script.
Use `--no-sync` after installing manifest dependencies so a subsequent `uv run`
does not prune packages that are absent from the repo's dev dependency group.
For a focused iteration run `uv run --no-sync pytest src/node-types/<code>/tests`.

Also compare against the latest released metadata with
`limescape-plugin compat --against <previous-meta.tar.gz>`; the default `compat`
command only checks builtin snapshots. Follow [.github/workflows/ci.yml](../.github/workflows/ci.yml)
for the full release gate: vulnerability audit, license check, clean-checkout
secret scan and reproducible bundle build. Passing unit tests is not equivalent
to passing CI. Follow the actual workflow when its commands change.

Documentation-only changes need link/schema/example checks as applicable; they
do not require running unrelated platform services or the full application suite.

## 6. Definition of done and future skill handoff

A new node is ready for review when its manifest, implementation, both locales,
README and tests agree; the three credential modes, email identity resolution
and type/value/scope assumptions are documented and supported where required;
relevant checks pass; and any remaining platform work is stated explicitly.
Its README must explain what users select, how they create the credential,
required permissions, inputs/outputs, an example flow and known limitations.

Report which tests actually ran. Treat credential-type migrations, OAuth support,
UI integration, release publication and activation as distinct deliverables.
If a platform addition is required, name the files and missing contract instead
of describing the plugin as ready to use. Follow the [release and localhost
activation instructions](../README.md#releasing) for an authorized release.

A future Claude skill can accept this brief and follow sections 1–6:

```text
Node purpose / code:
New node or existing-code override:
Input and output examples (synthetic):
External API operations and side effects:
Credential modes: selected personal code / selected team code / selected type:
Type name(s), exact property shape and personal owner/team scope:
Email identity aliases (user_id, user_email, email) and Deep Agent handoff:
Token lifecycle / provider permissions / platform prerequisites:
Compatibility constraints and acceptance cases:
```

Keep the skill entry point short: load `AGENTS.md`, this workflow and the
credential guide on demand. Reuse these reference files rather than copying a
second set of rules. A skill must verify supported SDK methods and the credential
schema before scaffolding authentication code.

## Platform references

Paths below are relative to the **platform** checkout (`../limescape-ai-platform`
when it is a sibling). Read its current instructions before working there.

| Source | What to verify |
| --- | --- |
| `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` | Agent workflow and GitNexus requirements |
| `.github/instructions/api.instructions.md` | Thin entry points, helpers and tracing intent |
| `.github/instructions/platform.instructions.md`, `.github/instructions/testing.instructions.md` | Code/config precedence, English docs, behavior tests |
| `docs/COPILOT_GOVERNANCE.md` | Platform review and ownership |
| `packages/limescape-plugin-sdk/src/limescape_plugin_sdk/manifest.py`, `catalog.py`, `context.py`, `capabilities.py` | Authoritative manifest, runtime and capability schemas |
| `packages/limescape-plugin-sdk/src/limescape_plugin_sdk/compat.py`, `testing/runner.py`, `testing/fake_context.py` | Compatibility rules and test-harness limits |
| `packages/truelime-ai/src/truelime_ai/platform/plugins/execution.py`, `ctx_server.py` | Parameter preparation, trusted execution scope and platform capabilities |
| `docs/plans/2026-09-26-limescape-ai-plugins-dynamische-node-types-plan.md`, `docs/plans/2026-09-26-limescape-ai-plugins-handover.md` | Design rationale; historical status can be superseded by code |
