"""Reddit content agent: discussion-style posts with hard anti-ban rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agent_framework import Agent

from advisor.client import get_chat_client
from advisor.log import log
from advisor.middleware import caching, llm_call_logging, retry, tool_call_logging
from advisor.models.reddit import RedditPost, RedditPostResponse
from advisor.tools.github_activity import github_activity
from advisor.tools.read_repo import read_repo

SAFE_SUBREDDITS: list[str] = [
    "programming",
    "ExperiencedDevs",
    "Python",
    "node",
    "MachineLearning",
    "devops",
    "LocalLLaMA",
    "learnprogramming",
]

SYSTEM_PROMPT = """\
You write Reddit posts for an experienced software engineer.

# HARD RULES — VIOLATING THESE GETS THE ACCOUNT BANNED

1. **No self-promotion in the first months / posts.** Never include a link to
   the author's own repo, project, blog, product, or LinkedIn unless the
   `allow_self_promo` flag is true *and* karma is high.
2. **No marketing language.** No "I built", no "check out", no "would love
   feedback", no "we're building", no "join us", no "DMs open".
3. **No CTAs that benefit the author.** No "follow me", no "see my profile".
4. **90/10 rule:** the post must be 90%+ value to the reader and ≤10%
   anything that could be construed as promotion. `self_promo_level` ≤ 1.
5. **Match subreddit culture.** Don't post a beginner question to
   r/ExperiencedDevs. Don't post a vague opinion to r/programming.
6. **No clickbait titles.** Reddit hates "You won't believe...". Be specific
   and literal: "Why X breaks Y when Z" beats "I made a discovery!".
7. **No repetitive posting patterns.** Vary subreddit, post_type, and angle
   from the user's recent history (provided in the prompt when relevant).
8. **Discussion-first.** Default `post_type` is "discussion" or "help" or
   "til". `show-and-tell` is only allowed when explicitly requested.

# Allowed post types
- discussion: open question / observation / debate-starter
- til: "TIL: <specific technical fact>" + body explaining
- help: a real engineering question you're stuck on
- show-and-tell: only when explicitly allowed

# Style
- Plain prose. Markdown headings sparingly. Code blocks where useful.
- 200-1200 chars body. Title ≤ 300 chars.
- End with a real question to the community when discussion type.
- Choose a subreddit from the safe list relevant to the topic.

# Safe subreddits (pick one)
programming, ExperiencedDevs, Python, node, MachineLearning, devops,
LocalLLaMA, learnprogramming.

Return a single RedditPost.
"""


async def generate_reddit_post(
    topic: str = "",
    allow_self_promo: bool = False,
    subreddit_hint: str = "",
) -> RedditPost | None:
    """Generate one Reddit post draft."""
    agent = Agent(
        client=get_chat_client(),
        name="reddit-agent",
        instructions=SYSTEM_PROMPT,
        tools=[github_activity, read_repo],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    prompt_lines = [
        "Generate ONE Reddit post draft.",
        f"Topic: {topic or '(open — pick the strongest angle from GitHub activity)'}",
        f"allow_self_promo={allow_self_promo}. Keep self_promo_level ≤ {1 if allow_self_promo else 0}.",
    ]
    if subreddit_hint:
        prompt_lines.append(f"Preferred subreddit (must still be in safe list): {subreddit_hint}")
    prompt_lines.append(
        "Use github_activity if the topic is open-ended; do not name the user's "
        "repo in the post body unless allow_self_promo is true."
    )
    prompt = "\n".join(prompt_lines)

    log.info("RedditAgent: topic=%s allow_self_promo=%s", topic or "(open)", allow_self_promo)
    response = await agent.run(prompt, options={"response_format": RedditPostResponse})

    if not response.value:
        log.error("RedditAgent failed: %s", response.text[:200])
        return None

    post = response.value.post
    post.id = post.id or uuid.uuid4().hex
    post.created_at = post.created_at or datetime.now(UTC).isoformat()
    if not allow_self_promo and post.self_promo_level > 1:
        log.warning(
            "RedditAgent returned self_promo_level=%d; clamping to 1",
            post.self_promo_level,
        )
        post.self_promo_level = 1
    if post.subreddit not in SAFE_SUBREDDITS:
        log.warning("RedditAgent picked unsafe subreddit %s; defaulting to programming", post.subreddit)
        post.subreddit = "programming"
    log.info(
        "RedditAgent draft: r/%s [%s] %s",
        post.subreddit,
        post.post_type,
        post.title[:80],
    )
    return post
