"""Pass through the text of a selected prompt (nested references resolved)."""

from limescape_plugin_sdk import NodeContext, NodeInput


async def execute(ctx: NodeContext, inp: NodeInput):
    prompt_id = inp.params.get("prompt_id")
    if prompt_id is None:
        # Same wording as the builtin, so stored runs and golden cases match.
        raise ValueError("prompt_id cannot be None")
    yield {inp.output_key: await ctx.prompts.get_text(prompt_id)}
