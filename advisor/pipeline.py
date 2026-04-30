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
from advisor.tools.generate_image import generate_image


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

        log.info("Draft saved: id=%s category=%s hook=%s", draft.id, draft.category, draft.hook[:60])
        log.info("Draft metadata: source=%s chars=%d image_suggestion=%s",
                 draft.source.type if draft.source else "none",
                 len(draft.body),
                 (draft.image_suggestion or "")[:80])

        full_text = draft.body if draft.body.startswith(draft.hook) else f"{draft.hook}\n{draft.body}"

        # Generate diagram for technical posts
        diagram_path = None
        if draft.category == "technical" and draft.image_suggestion:
            log.info("Generating diagram: prompt=%s", draft.image_suggestion[:100])
            diagram_path = generate_image(
                draft.image_suggestion,
                f"draft-{draft.id[:8]}.png",
                quality="medium",
            )
            if diagram_path:
                log.info("Diagram saved: %s (%d bytes)", diagram_path, diagram_path.stat().st_size)
            else:
                log.warning("Diagram generation failed")

        image_path = generate_preview_image(full_text, diagram_path=diagram_path)
        log.info("Preview saved: %s (%d bytes) diagram=%s", image_path, image_path.stat().st_size, bool(diagram_path))

        usage = get_token_usage()
        log.info("Draft created [%s]: %d tokens, est cost $%.4f",
                 run_id, usage.total_tokens, usage.total_tokens * 0.000005)
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

    full_text = revised.body if revised.body.startswith(revised.hook) else f"{revised.hook}\n{revised.body}"

    diagram_path = None
    if revised.category == "technical" and revised.image_suggestion:
        diagram_path = generate_image(revised.image_suggestion, f"draft-{post_id[:8]}.png", quality="medium")

    image_path = generate_preview_image(full_text, diagram_path=diagram_path)

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
