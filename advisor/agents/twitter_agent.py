"""Twitter/X content agent: short punchy hooks and threads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agent_framework import Agent

from advisor.client import get_chat_client
from advisor.log import log
from advisor.middleware import caching, llm_call_logging, retry, tool_call_logging
from advisor.models.twitter import TWEET_MAX, TwitterPost, TwitterPostResponse
from advisor.tools.github_activity import github_activity
from advisor.tools.read_repo import read_repo

SYSTEM_PROMPT = f"""\
You write tweets and threads for a senior AI / software engineer.

# Hard rules
- Lead tweet ≤ {TWEET_MAX} characters. Each thread tweet ≤ {TWEET_MAX} chars.
- If `as_thread` is requested: lead is a hook, then 3-8 follow-ups.
- If single tweet: punch in one shot.
- 1-3 hashtags max in `hashtags`. No hashtags inside the tweet text itself
  unless they read naturally.
- Emoji are OK but ≤ 2 per tweet.

# What works on this account's audience
- Hook formulas: bold claim, contrarian take, surprising metric, "X is
  underrated, here's why", story openers like "I rebuilt X over the weekend".
- Threads: numbered or step-based. Concrete, code-flavored, opinionated.
- No "🧵👇" cliché unless the content earns it.
- No begging for engagement ("RT if you agree").

# Structure (thread)
1. Lead: hook + promise (what the reader will get).
2. Body tweets: one idea per tweet. Code/numbers/specifics.
3. Closer: a pointed takeaway or a question.

Return a single TwitterPost.
"""


async def generate_twitter_post(topic: str = "", as_thread: bool = False) -> TwitterPost | None:
    """Generate a single tweet or a thread."""
    agent = Agent(
        client=get_chat_client(),
        name="twitter-agent",
        instructions=SYSTEM_PROMPT,
        tools=[github_activity, read_repo],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    prompt = (
        f"Generate ONE Twitter/X post.\n"
        f"Topic: {topic or '(open — pick from GitHub activity)'}\n"
        f"as_thread={as_thread}. "
        f"{'Produce a 4-7 tweet thread.' if as_thread else 'Single tweet only — leave thread empty.'}"
    )

    log.info("TwitterAgent: topic=%s thread=%s", topic or "(open)", as_thread)
    response = await agent.run(prompt, options={"response_format": TwitterPostResponse})

    if not response.value:
        log.error("TwitterAgent failed: %s", response.text[:200])
        return None

    post = response.value.post
    post.id = post.id or uuid.uuid4().hex
    post.created_at = post.created_at or datetime.now(UTC).isoformat()
    if not as_thread:
        post.thread = []
    log.info("TwitterAgent draft: %s (%d follow-ups)", post.text[:60], len(post.thread))
    return post
