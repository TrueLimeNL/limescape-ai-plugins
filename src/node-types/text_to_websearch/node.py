"""Google Custom Search override; the API key stays on the platform."""

import json

from limescape_plugin_sdk import NodeContext, NodeInput
from limescape_plugin_sdk.errors import CapabilityError


async def _search(ctx, query, params, max_results):
    # Extract search parameters
    search_type = params.get("searchType", "web")
    country = params.get("country", "US")
    language = params.get("language", "en")
    # Handle both 'count' and 'num' parameter names for backward compatibility
    num_results = min(
        int(params.get("count") or params.get("num") or max_results), 10
    )  # Google CSE API max is 10 per request
    start_index = int(params.get("startIndex") or params.get("start") or 1)  # Handle both parameter names

    # Handle safe search parameter with validation
    safe_search_raw = params.get("safeSearch", params.get("safe", "medium"))
    # Map common values to valid API values
    safe_search_mapping = {
        "Off": "off",
        "off": "off",
        "Medium": "medium",
        "medium": "medium",
        "High": "high",
        "high": "high",
        "Active": "active",
        "active": "active",
        "Moderate": "medium",  # Map old Bing value to medium
        "Strict": "high",  # Map old Bing value to high
    }
    safe_search = safe_search_mapping.get(safe_search_raw, "medium")  # Default to medium if invalid

    site_restrict = params.get("siteRestrict", "")
    date_restrict = params.get("dateRestrict", "")

    # Modify query to restrict to specific websites if provided
    if site_restrict:
        # Split comma-separated list of websites
        sites = [site.strip() for site in site_restrict.split(",") if site.strip()]
        if sites:
            # Create a site: query for each website
            site_queries = [f"site:{site}" for site in sites]
            # Join with OR operator for multiple sites
            site_query = " OR ".join(site_queries)
            # Combine with original query
            query = f"({query}) ({site_query})"

    try:
        # Build the Google Custom Search service

        # Prepare search parameters with correct parameter names
        search_params = {
            "q": query,
            "num": num_results,  # Correct parameter name
            "start": start_index,  # Correct parameter name
            "safe": safe_search,  # Correct parameter name
            "gl": country,
            "hl": language,
        }

        # Add search type (web or image)
        if search_type == "image":
            search_params["searchType"] = "image"

        # Add date restriction if provided
        if date_restrict:
            search_params["dateRestrict"] = date_restrict

        # Add any additional search parameters from the skill parameters
        search_parameters_json = params.get("searchParameters")
        if search_parameters_json:
            try:
                search_parameters = json.loads(search_parameters_json.replace("'", '"'))
                search_params.update(search_parameters)
            except Exception as e:
                ctx.log.error(f"Error parsing search parameters: {e}")

        # Perform the search
        request_query = search_params.pop("q")
        result = await ctx.websearch.search(str(request_query), parameters=search_params)

        # Process the results
        search_results = []

        if "items" in result:
            for item in result["items"]:
                if search_type == "image":
                    # Image search result format
                    search_result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "displayUrl": item.get("displayLink", ""),
                        "thumbnailUrl": item.get("image", {}).get("thumbnailLink", ""),
                        "contextUrl": item.get("image", {}).get("contextLink", ""),
                        "width": item.get("image", {}).get("width", 0),
                        "height": item.get("image", {}).get("height", 0),
                        "fileFormat": item.get("fileFormat", ""),
                        "mime": item.get("mime", ""),
                    }
                else:
                    # Web search result format
                    search_result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "displayUrl": item.get("displayLink", ""),
                        "formattedUrl": item.get("formattedUrl", ""),
                        "htmlTitle": item.get("htmlTitle", ""),
                        "htmlSnippet": item.get("htmlSnippet", ""),
                        "cacheId": item.get("cacheId", ""),
                        "fileFormat": item.get("fileFormat", ""),
                        "mime": item.get("mime", ""),
                    }
                search_results.append(search_result)

        # Add search metadata
        search_info = result.get("searchInformation", {})
        metadata = {
            "totalResults": search_info.get("totalResults", "0"),
            "searchTime": search_info.get("searchTime", 0),
            "formattedTotalResults": search_info.get("formattedTotalResults", ""),
            "formattedSearchTime": search_info.get("formattedSearchTime", ""),
        }

        # Return the search results with metadata
        yield {"results": search_results[:max_results], "metadata": metadata, "query": query}

    except Exception as e:
        if isinstance(e, CapabilityError) and e.code == "not_configured":
            raise ValueError(e.message) from e
        ctx.log.error(f"Error in Google Custom Search: {e}")
        yield [{"error": e.message if isinstance(e, CapabilityError) else str(e)}]


def _camel(name):
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


async def execute(ctx: NodeContext, inp: NodeInput):
    query = inp.params.get("search_query")
    if query in (None, ""):
        raw = inp.params.get("input_keys") or "text"
        keys = raw.split(",") if isinstance(raw, str) else raw if isinstance(raw, list) else []
        keys = [str(key).strip() for key in keys if str(key).strip()]
        missing = [key for key in keys if key not in inp.input_data]
        key = keys[0] if keys else "text"
        if missing:
            raise ValueError(f"Missing required input data: {missing} in {inp.node_name}")
        query = inp.input_data.get(key)
        if query in (None, ""):
            raise ValueError(f"Missing required input data: ['{key}'] in {inp.node_name}")
    # The builtin requires this execution metadata before calling the provider.
    _ = inp.input_data["assistant_code"]
    params = {_camel(key): value for key, value in inp.params.items()}
    max_results = 10
    if params.get("searchParameters"):
        try:
            additional = json.loads(params["searchParameters"].replace("'", '"'))
            max_results = additional.get("num", additional.get("count", 10))
        except Exception:
            max_results = 10
    async for result in _search(ctx, query, params, max_results):
        yield {inp.output_key: result}
