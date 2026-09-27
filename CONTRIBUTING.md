# Contributing

Pull requests are welcome from anyone. They are merged only after review by the
Limescape maintainers (see `.github/CODEOWNERS`) and when every `ci` check
passes.

* One node type per folder under `src/node-types/`; keep changes to one node
  type per pull request where possible.
* Keep node types stateless: executions of the same bundle version share a
  process.
* Never commit secrets, real customer data or production responses, also not
  in golden cases. Use synthetic data.
* Describe user-visible changes in the node type's `README.md`.

## Agent-assisted node development

Follow [AGENTS.md](AGENTS.md) and the [node-type workflow](docs/agent-node-types.md).
For integrations, document all three credential selection modes: a selected
personal code, a selected team code, or a selected type resolved per execution
for the user identified by `user_id`, `user_email` or `email`. Verify identity
propagation when a Deep Agent invokes the flow as a tool. Document the exact
value mapping, authentication lifecycle and any missing platform/SDK support
using the [credential guide](docs/credentials-and-node-types.md). A filtered credential
picker does not implement OAuth refresh or enforce credential types at runtime.

Write documentation in English and include Dutch and English node-form
translations. Add behavioral tests with short intent docstrings and synthetic
fixtures. State any required platform migration or capability change separately
from the plugin implementation.
