"""Tool: web-search successful posts in a niche using Tavily."""

from __future__ import annotations

import json

from agent_framework import tool
from shon_toolkit.log import log
from tavily import TavilyClient

from advisor.config import get_settings

_PLATFORM_QUERIES = {
    "linkedin": 'site:linkedin.com/posts "{niche}"',
    "reddit": 'site:reddit.com "{niche}"',
    "twitter": 'site:x.com OR site:twitter.com "{niche}"',
}


def _client() -> TavilyClient | None:
    key = get_settings().tavily_api_key
    if not key:
        log.warning("TAVILY_API_KEY not configured; copy research will return empty")
        return None
    return TavilyClient(api_key=key)


@tool
def copy_research(niche: str, platforms: str = "linkedin,reddit,twitter", limit: int = 5) -> str:
    """Search the web for successful posts in `niche` on the listed platforms.

    `platforms` is a comma-separated subset of: linkedin, reddit, twitter.
    Returns a JSON string with `{platform: [{title, url, snippet}]}` for the
    copy_agent to analyze.
    """
    client = _client()
    if client is None:
        return json.dumps({"error": "no_tavily_key", "results": {}})

    selected = [p.strip().lower() for p in platforms.split(",") if p.strip()]
    selected = [p for p in selected if p in _PLATFORM_QUERIES]

    out: dict[str, list[dict[str, str]]] = {}
    for plat in selected:
        query = _PLATFORM_QUERIES[plat].format(niche=niche)
        log.info("copy_research: querying %s -> %s", plat, query)
        try:
            resp = client.search(query=query, max_results=limit, search_depth="basic")
        except Exception as e:
            log.error("copy_research search failed for %s: %s", plat, e)
            out[plat] = []
            continue
        items = []
        for r in resp.get("results", [])[:limit]:
            items.append(
                {
                    "title": r.get("title", "")[:200],
                    "url": r.get("url", ""),
                    "snippet": (r.get("content") or "")[:600],
                }
            )
        out[plat] = items

    return json.dumps({"niche": niche, "results": out}, ensure_ascii=False, indent=2)
