# REST API

Compatible override of `input_restapi_json`. Outputs JSON **as a string**, as the builtin does.
Requests go through `ctx.http`; templates use Jinja2 and preserve the builtin fallback parsing.

Select a team credential using `credential_code`. Its values may define `auth_type`,
`auth_username`, `auth_password`, `auth_token`, `auth_custom_key` and `auth_custom_value`.
Legacy inline fields remain accepted for existing nodes. A credential lookup failure is an error.
