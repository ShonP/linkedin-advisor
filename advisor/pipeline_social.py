"""Pipeline orchestration for multi-platform content (Reddit, Twitter, daily digest, copy research)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from shon_toolkit.log import attach_file_handler, detach_file_handler, log, new_run_id
from shon_toolkit.middleware import reset_token_usage

from advisor.agents.copy_agent import run_copy_research
from advisor.agents.daily_digest import run_daily_digest
from advisor.agents.reddit_agent import generate_reddit_post
from advisor.agents.twitter_agent import generate_twitter_post
from advisor.db import PostsDB
from advisor.models.copy import CopyAnalysis
from advisor.models.post import PostDraft
from advisor.models.proposal import DailyDigest
from advisor.models.reddit import RedditPost
from advisor.models.twitter import TwitterPost


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def create_reddit_draft(
    topic: str = "",
    *,
    allow_self_promo: bool = False,
    subreddit_hint: str = "",
) -> tuple[PostDraft, RedditPost] | None:
    run_id = new_run_id()
    reset_token_usage()
    attach_file_handler()
    log.info("Reddit draft [%s] topic=%s sub=%s", run_id, topic or "(open)", subreddit_hint)
    try:
        post = await generate_reddit_post(
            topic=topic, allow_self_promo=allow_self_promo, subreddit_hint=subreddit_hint
        )
        if not post:
            return None
        draft = PostDraft(
            id=_new_id(),
            hook=post.title,
            body=post.body,
            category="reddit",
            source=post.source,
            image_suggestion="",
            best_time="",
            platform="reddit",
            created_at=_now(),
        )
        db = PostsDB()
        try:
            db.save_draft(draft, reddit=post)
            db.record_reddit_post(post.subreddit)
        finally:
            db.close()
        return draft, post
    finally:
        detach_file_handler()


async def create_twitter_draft(
    topic: str = "",
    *,
    as_thread: bool = False,
) -> tuple[PostDraft, TwitterPost] | None:
    run_id = new_run_id()
    reset_token_usage()
    attach_file_handler()
    log.info("Twitter draft [%s] topic=%s thread=%s", run_id, topic or "(open)", as_thread)
    try:
        post = await generate_twitter_post(topic=topic, as_thread=as_thread)
        if not post:
            return None
        body = "\n\n".join(post.thread) if post.thread else post.text
        draft = PostDraft(
            id=_new_id(),
            hook=post.text[:120],
            body=body,
            category="twitter",
            source=post.source,
            image_suggestion="",
            best_time="",
            platform="twitter",
            created_at=_now(),
        )
        db = PostsDB()
        try:
            db.save_draft(draft, twitter=post)
        finally:
            db.close()
        return draft, post
    finally:
        detach_file_handler()


async def create_linkedin_draft(topic: str = "") -> PostDraft | None:
    from advisor.pipeline import create_draft as _create_linkedin_with_image

    result = await _create_linkedin_with_image(topic)
    if not result:
        return None
    draft, _image_path = result
    draft.platform = "linkedin"
    return draft


async def run_copy_research_save(niche: str, platforms: list[str]) -> tuple[str, CopyAnalysis] | None:
    run_id = new_run_id()
    reset_token_usage()
    attach_file_handler()
    log.info("Copy research [%s] niche=%s", run_id, niche)
    try:
        analysis = await run_copy_research(niche=niche, platforms=platforms)
        if not analysis:
            return None
        analysis_id = _new_id()
        db = PostsDB()
        try:
            db.save_copy_analysis(analysis, analysis_id)
        finally:
            db.close()
        return analysis_id, analysis
    finally:
        detach_file_handler()


async def run_daily_digest_save(extra_topic: str = "") -> DailyDigest | None:
    run_id = new_run_id()
    reset_token_usage()
    attach_file_handler()
    log.info("Daily digest [%s]", run_id)
    try:
        digest = await run_daily_digest(extra_topic=extra_topic)
        if not digest:
            return None
        db = PostsDB()
        try:
            for proposal in digest.proposals:
                if not proposal.id:
                    proposal.id = _new_id()
                if not proposal.created_at:
                    proposal.created_at = _now()
                db.save_proposal(proposal)
        finally:
            db.close()
        return digest
    finally:
        detach_file_handler()


def run_async(coro):
    return asyncio.run(coro)
