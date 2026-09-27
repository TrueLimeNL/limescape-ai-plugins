# Coding-agent instructions

This repository contains dynamic node types for Limescape AI Platform. These
instructions apply to agents working here, including Claude Code via `CLAUDE.md`.

## Read before implementing

1. Read [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
2. Follow [the node-type workflow](docs/agent-node-types.md).
3. For any authenticated integration, read
   [the credential contract](docs/credentials-and-node-types.md) before designing
   fields or writing HTTP calls. Record the chosen credential type, value shape,
   selection mode, identity source and authentication lifecycle in the node's README.
4. Inspect the closest existing node and its tests, and check `compat/legacy/`
   for a code collision. Existing nodes can contain intentional legacy behavior;
   do not copy it into a new contract without checking the guide.

## Boundaries

- Create `src/node-types/<code>/node-type.yaml`, `node.py`, `i18n/nl.json`,
  `i18n/en.json`, `README.md` and behavior tests. Folder name equals manifest code.
- The plugin entry point is an async generator: `execute(ctx, inp)`.
  Import only the standard library, `limescape_plugin_sdk`, declared third-party
  dependencies and relative helpers inside the same node folder.
- Keep execution orchestration small and transformations pure. The SDK loader
  supports `from .helper import ...`. Never import `truelime_ai`, Django, another
  node type or platform tracing decorators into a plugin.
- Use manifest capabilities and `ctx` for platform operations. The current SDK
  exposes `http`, `credentials`, `prompts` and `websearch`; `network` is only a
  declaration for direct network use. `log` and `trace` are implicit capabilities.
  Do not invent methods such as `ctx.credentials.refresh()` or `ctx.llm`.
- Keep nodes stateless. A host process can serve multiple executions and teams;
  never cache credential values, clients carrying secrets or request data globally.
- Preserve output shapes, parameter names, choice values and lookup targets.
  Deprecate old fields/types; give a breaking contract a new node code. Never
  rewrite `compat/legacy/` or golden expectations to conceal incompatibility.
- Prefer `ctx.http` for network access. Use bounded timeouts; retry mutations only
  with an explicit idempotency policy. Keep secrets and raw sensitive responses
  out of outputs, exception messages, logs and traces.

## Credentials: three required selection modes

For a node that needs a user-configured credential, follow this functional
contract. Do not reduce it to the team-only SDK example:

1. **Selected personal credential:** save its `Credential.code` in the node and
   resolve that specific instance within the execution team for every caller,
   including callers other than its owner. This deliberately shares the selected
   credential through the flow; never substitute the executing user’s instance.
2. **Selected team credential:** save its `Credential.code` in the node and
   resolve that specific active team instance.
3. **Selected credential type:** save `CredentialType.name` as a type selection,
   then resolve the executing person's personal credential of that type per run.
   Determine their email from the flow inputs `user_id`, `user_email` or `email`
   using platform identity resolution. This is especially important when a Deep
   Agent invokes the flow as a tool: the same flow must use each caller's own
   credential, not a credential fixed to the flow author.

- Keep selection mode, credential instance code and credential type distinct.
  Never infer a type selection from a code prefix or store secrets in parameters.
- Scope every resolution to the execution team and the selected personal/team
  mode. For type selection, resolve the email to a platform user before looking
  up that user's active credential. Missing or ambiguous identity/credentials
  must fail clearly; personal resolution must not silently fall back to a team
  credential or a different person.
- Preserve the caller's identity through Deep Agent tool dispatch and nested
  flow input mapping. Identity inputs identify a user; platform authorization
  still determines whether the execution may use that user's credentials.
- Use mode-specific editor lookups. `user__isnull: true` belongs to the team
  picker only; a fixed personal picker uses the execution team and
  `user__isnull: false` (sharing is intentional), and type mode
  selects a supported `CredentialType.name`. Validate exact type/value contracts.
- With SDK **0.2.2** and the accompanying platform changes, use
  `ctx.credentials.resolve(reference, mode=..., expected_type=..., oauth2=...)`.
  Modes are `personal`, `team`, `personal_type`; the platform binds team/identity
  and enforces exact types. `oauth2=True` currently supports GTM only.
- Legacy `ctx.credentials.get(code)` remains team-only, has no OAuth lifecycle
  and does not populate `Credential.type_name`. Do not use it for the three-mode
  contract. SDK 0.2.2 must be published/installed and platform changes deployed
  before activating the new node; source code is not proof of deployment.
- Credential keys are not normalized: `accessToken`, `auth_token` and
  `secrets.api_key` are different contracts. Use documented values and platform
  preset overlays; never expose refresh/client secrets in node parameters.

See [the credential guide](docs/credentials-and-node-types.md) for resolution,
Deep Agent propagation, current implementation gaps and acceptance cases.

## Working with the platform repository

The usual sibling checkout is `../limescape-ai-platform`. Locate it rather than
hardcoding a developer's absolute path. If it is absent, use these guides and the
installed SDK; clearly mark any platform prerequisite that you cannot verify.

Before changing platform files, read that checkout's `AGENTS.md`, `CLAUDE.md`,
`.github/copilot-instructions.md` and applicable `.github/instructions/` files.
Follow its GitNexus exploration/impact requirements and report unresolved graph
analysis. Platform rules for builtin `tasks.py`, versioning and imports do not
replace the dynamic plugin contract here. Preserve unrelated local changes.

## Verification and handoff

- Follow the commands and completion checklist in [the workflow](docs/agent-node-types.md).
  Use the SDK version pinned in `pyproject.toml` and Python 3.12.
- Run relevant behavioral tests with `FakeContext(granted=...)`; verify failures
  as well as success. Fakes do not prove database scoping, UI lookup or OAuth flow.
- Document changes in English, with both Dutch and English UI translations.
- Report changed files, the credential contract, checks actually run and remaining
  platform/activation prerequisites. Keep release publishing and activation
  separate from node implementation unless the user requested them.
