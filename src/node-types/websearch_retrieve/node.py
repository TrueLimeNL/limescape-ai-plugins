"""Fetch websearch URLs and extract text with the builtin result format."""

import asyncio
import json

from bs4 import BeautifulSoup
from limescape_plugin_sdk import NodeContext, NodeInput

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


async def _fetch(ctx, url):
    for attempt in range(3):
        try:
            response = await ctx.http.request("GET", url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if response.status != 200:
                return {"url": url, "content": "", "status_code": response.status}
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style"]):
                element.decompose()
            lines = (line.strip() for line in soup.get_text().splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            return {
                "url": url,
                "title": soup.title.string if soup.title else "No title",
                "content": text[:10000],
                "status_code": response.status,
            }
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2)


async def execute(ctx: NodeContext, inp: NodeInput):
    results = inp.input_data.get(inp.params.get("input_keys", "search_results"), [])
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except json.JSONDecodeError:
            yield {inp.output_key: f"Error: Could not parse input as JSON: {results[:100]}..."}
            return
    urls = (
        [result["url"] for result in results if isinstance(result, dict) and "url" in result]
        if isinstance(results, list)
        else []
    )
    if not urls:
        yield {inp.output_key: "No URLs found in the search results"}
        return
    urls = urls[: int(inp.params.get("max_urls", 3))]
    yield {inp.output_key: [await _fetch(ctx, url) for url in urls]}
