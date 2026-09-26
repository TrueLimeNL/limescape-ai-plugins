"""Transform text: trim, change case, or find and replace."""

from collections.abc import Callable

from limescape_plugin_sdk import NodeContext, NodeInput, NodeInputError

_OPERATIONS: dict[str, Callable[[str], str]] = {
    "strip": str.strip,
    "upper": str.upper,
    "lower": str.lower,
    "title": str.title,
}


async def execute(ctx: NodeContext, inp: NodeInput):
    text = inp.param("text", "")
    if not isinstance(text, str):
        text = str(text)
    operation = inp.param("operation", "strip")

    if operation == "replace":
        find = inp.param("find", "")
        if not find:
            raise NodeInputError("parameter 'find' is required for find and replace")
        result = text.replace(find, inp.param("replace_with", ""))
    elif operation in _OPERATIONS:
        result = _OPERATIONS[operation](text)
    else:
        raise NodeInputError(f"unknown operation '{operation}'")

    ctx.log.debug("text transformed", operation=operation, length=len(result))
    yield {inp.output_key: result}
