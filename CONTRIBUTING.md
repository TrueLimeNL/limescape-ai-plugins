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
