# Transform text

Applies one transformation to a text and yields the result under the node's
output key.

| Operation | Result |
|---|---|
| Trim whitespace | removes leading and trailing whitespace |
| Uppercase / Lowercase / Title case | changes the case |
| Find and replace | replaces every occurrence of *Find* with *Replace with* |

The text can contain `{{ variable }}` references to earlier nodes; the platform
resolves them before the node runs.
