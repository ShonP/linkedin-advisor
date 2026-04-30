"""Pipeline: generate drafts, manage approvals, render previews."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from advisor.agents.content_creator import edit_post_draft, generate_single_draft
from advisor.db import PostsDB
from advisor.log import attach_file_handler, detach_file_handler, log, new_run_id
from advisor.middleware import get_token_usage, reset_token_usage
from advisor.models.post import PostDraft
from advisor.preview import generate_preview_image


async def create_draft(topic: str = "") -> tuple[PostDraft, Path] | None:
    """Generate a single draft, save to DB, render preview image."""
    run_id = new_run_id()
    reset_token_usage()
    attach_file_handler()
    log.info("Creating draft [%s] topic=%s", run_id, topic or "(open)")

    try:
        draft = await generate_single_draft(topic)
        if not draft:
            log.warning("No draft generated")
            return None

        if not draft.created_at:
            draft.created_at = datetime.now(UTC).isoformat()

        db = PostsDB()
        try:
            db.save_draft(draft)
        finally:
            db.close()

        full_text = f"{draft.hook}\n{draft.body}"
        image_path = generate_preview_image(full_text)

        usage = get_token_usage()
        log.info("Draft created [%s], %d tokens", run_id, usage.total_tokens)
        return draft, image_path
    except Exception:
        log.exception("Draft creation failed")
        raise
    finally:
        detach_file_handler()


def approve_draft(post_id: str) -> bool:
    """Mark a draft as approved."""
    db = PostsDB()
    try:
        ok = db.approve(post_id)
        if ok:
            log.info("Approved draft %s", post_id)
        return ok
    finally:
        db.close()


def reject_draft(post_id: str) -> bool:
    """Mark a draft as rejected."""
    db = PostsDB()
    try:
        ok = db.reject(post_id)
        if ok:
            log.info("Rejected draft %s", post_id)
        return ok
    finally:
        db.close()


async def edit_draft(post_id: str, instructions: str) -> tuple[PostDraft, Path] | None:
    """Revise an existing draft with edit instructions, re-render preview."""
    db = PostsDB()
    try:
        post = db.get_post(post_id)
    finally:
        db.close()

    if not post:
        log.warning("Post %s not found for editing", post_id)
        return None

    original_text = f"{post['hook']}\n{post['body']}"
    revised = await edit_post_draft(original_text, instructions)
    if not revised:
        return None

    revised.id = post_id
    revised.created_at = str(post.get("created_at", ""))

    db = PostsDB()
    try:
        db.update_draft_content(post_id, revised.hook, revised.body)
    finally:
        db.close()

    full_text = f"{revised.hook}\n{revised.body}"
    image_path = generate_preview_image(full_text)

    log.info("Edited draft %s", post_id)
    return revised, image_path


def list_approved() -> list[dict[str, object]]:
    """Return all approved drafts."""
    db = PostsDB()
    try:
        return db.list_approved()
    finally:
        db.close()


async def run_pipeline() -> str:
    """Run the content generation pipeline (backward-compatible entry point)."""
    result = await create_draft()
    if result:
        draft, image_path = result
        return f"Generated draft '{draft.hook[:50]}...' — preview: {image_path}"
    return "No draft generated."


def run_pipeline_sync() -> str:
    """Synchronous wrapper for the pipeline."""
    return asyncio.run(run_pipeline())
