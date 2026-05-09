"""Copy Agent: research successful posts and extract reusable patterns."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agent_framework import Agent

from advisor.client import get_chat_client
from advisor.log import log
from advisor.middleware import caching, llm_call_logging, retry, tool_call_logging
from advisor.models.copy import CopyAnalysis, CopyAnalysisResponse
from advisor.tools.copy_research import copy_research

SYSTEM_PROMPT = """\
You are a content strategist researching what works on LinkedIn, Reddit, and Twitter/X
for technical creators in: AI, dev tools, open source, Azure, system design.

## Your job
1. Call the `copy_research` tool with the requested niche and platforms.
2. Read the snippets you got back. Identify *what actually performed*: hooks,
   structure, tone, hashtag usage, engagement triggers, and platform-specific
   norms.
3. Produce a structured CopyAnalysis. Be concrete. Quote exact phrases when you
   cite an example. Don't fabricate URLs you didn't see.

## Per-platform rules to capture in `tones`
- LinkedIn: storytelling, professional, 1200-1500 chars, no hashtags spam.
  Hook formulas: curiosityGap, boldClaim, storyOpener, metric.
- Reddit: discussion-style, value-first, NO self-promotion in first posts.
  Different subreddits have different cultures — match them. Tone is plain,
  no marketing language. Markdown. Often a question at the end.
- Twitter/X: short punchy hooks, threads for depth, emoji and 1-3 hashtags,
  numbered lists work well, "how I X in N steps" is a common pattern.

## Output rules
- `patterns`: 5-10 reusable patterns with `name`, `description`, `example`.
- `examples`: 3-8 PostExample entries from your search results, with platform
  and snippet.
- `tones`: one ToneGuideline per requested platform.
- `top_hook_categories`: which hook types dominate the corpus.
- `summary`: 2-3 sentences capturing the takeaway.

Be specific and useful. Avoid generic advice like "be authentic".
"""


async def run_copy_research(niche: str, platforms: list[str] | None = None) -> CopyAnalysis | None:
    """Run the copy agent and return a structured CopyAnalysis."""
    plats = platforms or ["linkedin", "reddit", "twitter"]

    agent = Agent(
        client=get_chat_client(),
        name="copy-agent",
        instructions=SYSTEM_PROMPT,
        tools=[copy_research],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    prompt = (
        f"Research successful posts for the niche: '{niche}'.\n"
        f"Target platforms: {', '.join(plats)}.\n"
        "Use the copy_research tool first, then synthesize a CopyAnalysis."
    )

    log.info("CopyAgent: niche=%s platforms=%s", niche, plats)
    response = await agent.run(prompt, options={"response_format": CopyAnalysisResponse})

    if not response.value:
        log.error("CopyAgent failed, raw: %s", response.text[:200])
        return None

    analysis = response.value.analysis
    analysis.niche = analysis.niche or niche
    analysis.platforms = analysis.platforms or plats  # type: ignore[assignment]
    analysis.created_at = analysis.created_at or datetime.now(UTC).isoformat()
    log.info(
        "CopyAgent produced analysis: %d patterns, %d examples",
        len(analysis.patterns),
        len(analysis.examples),
    )
    return analysis


def new_analysis_id() -> str:
    return uuid.uuid4().hex
