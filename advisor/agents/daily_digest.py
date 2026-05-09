"""Daily Digest agent: scan recent activity, propose 3-5 cross-platform posts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agent_framework import Agent
from pydantic import BaseModel
from shon_toolkit.client import get_chat_client
from shon_toolkit.log import log
from shon_toolkit.middleware import caching, llm_call_logging, retry, tool_call_logging
from shon_toolkit.tools.github_activity import github_activity

from advisor.models.proposal import ContentProposal, DailyDigest
from advisor.tools.read_digest import read_digest
from advisor.tools.read_repo import read_repo
from advisor.tools.read_reports import read_reports

SYSTEM_PROMPT = """\
You are a multi-platform content planner. Every morning you scan the user's
GitHub activity from the last 24h, recent research reports, and the news
digest, then propose 3-5 *concrete* posts the user could publish today across
LinkedIn / Reddit / Twitter.

# Process
1. Call `github_activity(days=1)` to get yesterday's commits, PRs, repos.
2. Optionally call `read_reports` and `read_digest` for context.
3. For each proposal, decide: which platform fits this story best?
   - LinkedIn: longer narrative, personal angle, professional reach.
   - Reddit: discussion / TIL / help question that's *useful* to the
     community. Pick a subreddit from the safe list. Avoid self-promo.
   - Twitter: short punchy take, contrarian, or a thread of 4-7 tweets.
4. Each ContentProposal must include: platform, headline, angle, reasoning
   (why this works — pattern, audience fit, timing), confidence 0..1,
   source_summary citing the GitHub fact / report finding it's based on.

# Reddit safety
Never propose a Reddit show-and-tell with a self-link. Default Reddit type is
"discussion". Suggested_subreddit must be one of:
programming, ExperiencedDevs, Python, node, MachineLearning, devops,
LocalLLaMA, learnprogramming.

# Quality bar
- Each proposal must be different in *angle*, not the same story re-cut.
- Confidence reflects how strong the underlying signal is. >0.7 only if the
  GitHub fact is concrete and the angle is sharp.
- 3-5 proposals total — not more.
"""


class _DigestResponse(BaseModel):
    digest: DailyDigest


async def run_daily_digest(extra_topic: str = "") -> DailyDigest | None:
    """Scan activity and produce a DailyDigest of 3-5 ContentProposals."""
    agent = Agent(
        client=get_chat_client(),
        name="daily-digest",
        instructions=SYSTEM_PROMPT,
        tools=[github_activity, read_repo, read_reports, read_digest],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    prompt_lines = [
        "Scan the last 24h of GitHub activity (days=1) and propose 3-5 cross-platform "
        "post ideas. Use the tools first. Return a DailyDigest."
    ]
    if extra_topic:
        prompt_lines.append(f"User-specified angle for today: {extra_topic}")

    log.info("DailyDigest: extra_topic=%s", extra_topic or "(none)")
    response = await agent.run("\n".join(prompt_lines), options={"response_format": _DigestResponse})

    if not response.value:
        log.error("DailyDigest failed: %s", response.text[:200])
        return None

    digest = response.value.digest
    now = datetime.now(UTC).isoformat()
    cleaned: list[ContentProposal] = []
    for p in digest.proposals:
        p.id = p.id or uuid.uuid4().hex
        p.created_at = p.created_at or now
        cleaned.append(p)
    digest.proposals = cleaned[:5]
    log.info("DailyDigest produced %d proposals", len(digest.proposals))
    return digest
