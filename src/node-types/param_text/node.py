"""Static text: yields the configured text (variables are resolved by the platform)."""

from limescape_plugin_sdk import NodeContext, NodeInput


async def execute(ctx: NodeContext, inp: NodeInput):
    # Like the builtin: a missing value yields None, not an empty string.
    yield {inp.output_key: inp.params.get("text_value")}
