# limescape-ai-plugins

Node types for the Limescape AI Platform. The platform loads a released bundle
of this repository at runtime: new and changed node types appear in the flow
editor without a platform release.

Design: `docs/plans/2026-09-26-limescape-ai-plugins-dynamische-node-types-plan.md`
in the platform repository.

## How it works

* The whole repository is released as one bundle with one version (tag `v1.4.2`).
* A node type imports only [`limescape-plugin-sdk`](https://pypi.org/project/limescape-plugin-sdk/)
  and the dependencies it declares, never the platform.
* The CI guarantees that a node type meets the platform's requirements; the
  platform does not test again. It only checks the release checksum and that
  it supports the bundle's SDK version.
* A run pins the bundle version it started with; activating a new version
  only affects new runs.
* A node type with the code of a builtin (hardcoded) node type takes over that
  builtin. It must be backward compatible with the snapshot in
  `compat/legacy/` and prove equivalence with golden cases.

## Layout

```
src/node-types/<code>/
├── node-type.yaml     # manifest: the single source of metadata
├── node.py            # async def execute(ctx, inp)
├── i18n/nl.json       # nl and en are required
├── i18n/en.json
├── icon.svg           # optional; otherwise a Lucide name in the manifest
├── README.md          # user documentation
└── tests/
    ├── test_node.py
    └── golden/*.yaml  # required when overriding a builtin node type
compat/legacy/         # frozen snapshots of the builtin node types
```

## Adding a node type

1. Copy `src/node-types/text_transform` and rename the folder to the new code
   (`^[a-z][a-z0-9_]{2,63}$`).
2. Describe the form in `node-type.yaml` (same shape as the platform's
   `form_fields` / `form_layout`) and translate every label in `i18n/`.
3. Implement `execute` in `node.py`; declare every `ctx` capability you use and
   every third-party package under `dependencies`.
4. Run the checks locally:

```
uv sync
limescape-plugin validate
pytest
limescape-plugin golden
```

### Rules the CI enforces

* Never remove, rename or retype a form field; mark it `deprecated: true`.
  New required fields need a `default`.
* A real breaking change gets a new code name; set `stage: deprecated` on the old one.
* No imports of `truelime_ai`, of other node types, or of undeclared packages.
* Dependencies must resolve together with all other node types, have wheels for
  CPython 3.12 linux/amd64, an allowed licence and no known vulnerabilities.
* Icons must be inert (no scripts, event handlers or external references).

## SDK and current node types

This repository uses SDK **0.2.1** and Python 3.12. SDK 0.2.1 includes the
EUPL-1.2 licence metadata and licence file required by CI. Publish this SDK
version before running CI and deploy a platform with SDK 0.2.1 or a newer
compatible patch before activating a bundle; SDK 0.2.0 cannot activate a
0.2.1 bundle. Until publication, install the SDK from the sibling platform
checkout or its locally built wheel.

The initial bundle contains `text_transform` plus the overrides `param_text`,
`prompt_to_text`, `input_restapi_json`, `text_to_websearch` and `websearch_retrieve`.
Golden cases preserve the builtin behavior. Search uses the platform's
`websearch` capability; HTTP and credential lookups also pass through `ctx`.

## Releasing

Maintainers tag `main`: `git tag v1.4.2 && git push origin v1.4.2`.
`release.yml` checks the tag, builds with the exact lock and wheels tested by CI,
and publishes the archives and `SHA256SUMS`. The release notes contain the
version and activation hash for manual activation by a platform superuser.

Automatic activation on tst is optional. To enable it, set the **repository**
variable `PLUGINS_TST_AUTO_ACTIVATE` to `true` under Settings → Secrets and
variables → Actions → Variables, and configure the `tst-activation` environment
as described below. Leave the variable unset for local development; the release
is published normally and the activation job is skipped.

### Activating on localhost

GitHub-hosted runners cannot reach your local platform at `localhost:8000`.
Activate a published bundle yourself:

1. Run a platform with SDK 0.2.1 or a newer compatible patch, apply the
   `plugin_manager` migrations, and set `PLUGINS_ENABLED=1` on web, api and worker.
   Restart these services after changing their environment settings.
2. Make sure the platform can download the release assets. The default downloader
   uses unauthenticated GitHub release URLs, so the repository must be public
   for this route; a private repository needs a separately configured artifact
   source.
3. Log in as a superuser at `http://localhost:8000/plugins/` and activate the
   bundle with its version (without `v`) and activation hash from the release notes.
4. Refresh the flow editor and run a flow using `text_transform`.

Local manual activation does not require `PLATFORM_TST_URL`,
`PLUGINS_TST_ACTIVATION_TOKEN` or `PLUGINS_RELEASE_TOKEN`.

## Repository settings (governance)

The checksum protects against tampering in transit, not against a bad release,
so these settings carry the weight:

- [ ] Branch protection on `main`: pull request required, CODEOWNERS review,
      all `ci` checks required, no force pushes.
- [ ] Tag ruleset for `v*`: creation restricted to maintainers, no deletion,
      no updates.
- [ ] Release assets are only uploaded by `release.yml`; no manual uploads.
- [ ] For automatic tst activation: repository variable
      `PLUGINS_TST_AUTO_ACTIVATE=true` and environment `tst-activation` with
      deployment rule "tags: v*", variable `PLATFORM_TST_URL` and secret
      `PLUGINS_TST_ACTIVATION_TOKEN` (matching `PLUGINS_RELEASE_TOKEN` on the tst API).
- [ ] Actions: "Require approval for all outside collaborators" for fork PRs.
- [ ] Dependabot security updates enabled.

## Licence

To be decided before the repository is made public.
