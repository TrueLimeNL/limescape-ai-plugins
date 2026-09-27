# Google Tag Manager implementation validation

Checked locally on 2026-09-27 with CPython 3.12, the locally built SDK 0.2.2 wheel
and the matching platform checkout. This records development evidence, not a
published release or a live Google-account test.

| Check | Result |
| --- | --- |
| Plugin unit tests | 66 passed, including 47 GTM cases |
| Existing builtin golden cases | 57 passed |
| SDK suite | 68 passed |
| Host/protocol suite | 18 passed, including `credentials.resolve` RPC |
| Platform plugin/credential/Deep Agent suites | 242 passed; 6 external integration tests deselected |
| GTM web/database tests | 4 passed with an isolated SQLite database |
| Existing API credential-form tests | 10 passed |
| Manifests, imports, translations, Ruff, per-node mypy and Bandit | Passed |
| Legacy and published `v0.1.0` metadata compatibility | Passed |
| Hash-pinned offline dependency installation | Passed |
| License allowlist and Gitleaks | Passed |
| Two complete bundle builds | Identical SHA256SUMS |
| Platform workspace lock consistency | `uv lock --check --offline` passed |
| Dependency audit | No known vulnerabilities in audited dependencies; unpublished SDK 0.2.2 skipped by PyPI audit |

There are 408 passing tests across the six suites, plus 57 golden cases. After
final query/format changes, the affected resolver, web and SDK tests were rerun.

The platform tests establish fixed personal sharing, strict team/personal
selection, type/active-state checks, ambiguous-code rejection, active team
membership, each identity alias, alias conflicts and no fallback. OAuth tests
cover refresh-only credentials, near-expiry refresh, rotated token persistence,
concurrent refresh and neutral provider errors. The web test also exercises the
actual Google authorization redirect/scopes without contacting Google.

GitNexus was refreshed and its final change analysis reports low risk (16 tracked
files, 39 symbols). Its process graph has analysis limits and does not prove
absence of other callers; source inspection and the runtime tests supplement it.
New untracked implementation/migration files were reviewed and tested separately.

Before use, publish/install SDK 0.2.2, deploy the platform/worker changes, apply
credential migration 0026 and build/activate a new plugin release. Configure and
authorize a GTM credential, then smoke-test `list_accounts` against your account.
No real GTM writes, publication, production migrations or release activation were
performed as part of these checks.

See the [node README](../src/node-types/google_tag_manager/README.md) for all
fields, actions, credential behavior and rollout prerequisites.

## Category follow-up

The node now belongs to `marketing_analytics`, displayed as **Marketing & Analytics**.
The SDK and platform category catalogs are extended together within SDK 0.2.2;
existing 0.2.x bundles retain their compatibility. The palette smoke check uses
the actual GTM manifest and verifies membership in the new category only, matching
SDK/platform category IDs and both Dutch/English labels. SDK tests (68), GTM tests
(47), registry tests (11) and agent-detail configuration tests (2) passed.
Django `makemessages` and `compilemessages` were run; all pre-existing translations
were preserved and no fuzzy entries remain. GitNexus reported UNKNOWN for the
category/translation constants, so their direct uses were checked in source.
