# Pass through the text of a selected prompt

Outputs the text of the selected prompt (team or global) with nested prompt
references resolved. An unknown prompt yields an empty text.

Takes over the builtin node type `prompt_to_text`; the golden cases in
`tests/golden/` were recorded from the builtin.
