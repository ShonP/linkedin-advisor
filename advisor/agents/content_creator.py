"""Content creator agent: generates LinkedIn post drafts with structured output."""

from __future__ import annotations

from agent_framework._agents import Agent

from advisor.client import get_chat_client
from advisor.config import get_settings
from advisor.log import log
from advisor.middleware import caching, llm_call_logging, retry, tool_call_logging
from advisor.models.post import PostDraft, PostDrafts
from advisor.tools.github_activity import github_activity
from advisor.tools.read_digest import read_digest
from advisor.tools.read_reports import read_reports

SYSTEM_PROMPT = """\
You are a LinkedIn content strategist for a senior AI engineer.

Your job is to generate compelling LinkedIn post drafts based on the engineer's actual work,
recent news, and research findings. Each post must feel authentic and technically credible.

## Voice & Tone
- Write as a senior engineer sharing real experience, NOT as a marketer
- Practical, technical, candid, evidence-backed
- Show judgment and trade-offs, not just hype
- Use first person naturally: "I built...", "We discovered...", "I spent 3 days..."

## Post Structure
- Hook (first line): Must stop the scroll. Use one of these formulas:
  * "I analyzed X and found Y..."
  * "Most engineers get X wrong..."
  * "I spent [time] on [thing]. Here's what actually worked."
  * A bold claim or surprising finding
  * A specific number or metric
- Body: 1200-1500 characters total (including hook)
- End with a question or insight that invites comments
- NO hashtags in the post body
- NO external links in the post body
- Use line breaks for readability (short paragraphs, 2-3 sentences max)

## Categories
- technical: Production lessons, architecture decisions, implementation details
- insight: Opinions, contrarian takes, industry observations
- story: Personal narratives, project journeys, failure/success stories
- trend: Commentary on new tools, papers, benchmarks, industry shifts

## Quality Gates
- Must reference specific tech, tools, or metrics (not vague)
- Must include a personal angle or opinion (not just facts)
- Must have tension or surprise (not obvious)
- Must be useful to the reader (they learn something)
- Avoid: "excited to announce", "in today's rapidly evolving", "game-changer", "AI thought leader"

## Process
1. Use github_activity to check what the engineer has been working on recently
2. Use read_digest to get the latest AI/tech news
3. Use read_reports to find deep research insights
4. Generate 3-5 diverse post drafts from different sources and categories
5. Each draft should have a unique angle and source

Suggest an image idea and best posting time for each draft.
Best posting times: Tuesday-Thursday, 8-10am EST or 12-1pm EST.
"""


async def generate_post_drafts() -> list[PostDraft]:
    """Run the content creator agent and return structured PostDraft list."""
    settings = get_settings()
    username = settings.github_username or "octocat"

    agent = Agent(
        client=get_chat_client(),
        name="content-creator",
        instructions=SYSTEM_PROMPT,
        tools=[github_activity, read_digest, read_reports],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    prompt = (
        f"Generate LinkedIn post drafts for the engineer with GitHub username '{username}'. "
        "First, gather context by checking their recent GitHub activity, the latest news digest, "
        "and any available research reports. Then create 3-5 diverse post drafts."
    )

    log.info("Starting content generation for @%s", username)
    response = await agent.run(prompt, options={"response_format": PostDrafts})

    if response.value:
        drafts = response.value.drafts
        log.info("Content creator generated %d drafts", len(drafts))
        return drafts

    log.error("Content creator failed to produce structured output, raw: %s", response.text[:200])
    return []
