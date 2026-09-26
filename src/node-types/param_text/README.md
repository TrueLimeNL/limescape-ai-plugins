# Static text

Outputs the configured text under the node's output key. `{{ variable }}`
references to earlier nodes are resolved by the platform before the node runs.

Takes over the builtin node type `param_text`; the golden cases in
`tests/golden/` were recorded from the builtin.
