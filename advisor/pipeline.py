"""Pipeline: generate drafts, manage approvals, render previews."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from advisor.agents.content_creator import edit_post_draft, generate_single_draft
from advisor.db import PostsDB
from advisor.log import attach_file_handler, detach_file_handler, log, new_run_id
from advisor.middleware import get_token_usage, reset_token_usage
from advisor.models.post import PostDraft
from advisor.preview import generate_preview_image
from advisor.tools.generate_image import generate_image

_DIAGRAM_PROMPT_PREFIX = (
    "Clean minimal tech architecture diagram. Dark background (#1B1F23). "
    "Modern flat design with blue boxes (#0a66c2), white text, gray arrows. "
    "Show connected components with icons. Layout: left to right. "
)


def _build_diagram_prompt(image_suggestion: str) -> str:
    return f"{_DIAGRAM_PROMPT_PREFIX}{image_suggestion}"


def _generate_diagram(post_id: str, image_suggestion: str, category: str) -> Path | None:
    if category != "technical" or not image_suggestion:
        return None
    prompt = _build_diagram_prompt(image_suggestion)
    log.info("Generating diagram: prompt=%s", prompt[:120])
    path = generate_image(prompt, f"draft-{post_id[:8]}.png", quality="medium")
    log.info("Diagram %s: %s", "saved" if path else "failed", path or "N/A")
    return path


def _render_preview(hook: str, body: str, diagram_path: Path | None = None) -> Path:
    full_text = body if body.startswith(hook) else f"{hook}\n{body}"
    return generate_preview_image(full_text, diagram_path=diagram_path)

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

        diagram_path = _generate_diagram(draft.id, draft.image_suggestion, draft.category)
        image_path = _render_preview(draft.hook, draft.body, diagram_path)
        log.info("Preview saved: %s diagram=%s", image_path, bool(diagram_path))

        # Build full diagram prompt for metadata
        diagram_prompt_full = _build_diagram_prompt(draft.image_suggestion) if draft.image_suggestion else None

        # Save run metadata
        metadata = {
            "run_id": run_id,
            "topic": topic,
            "draft_id": draft.id,
            "category": draft.category,
            "hook": draft.hook,
            "body": draft.body,
            "body_chars": len(draft.body),
            "source": draft.source.model_dump() if draft.source else None,
            "image_suggestion": draft.image_suggestion,
            "diagram_prompt_full": diagram_prompt_full,
            "diagram_generated": diagram_path is not None,
            "diagram_path": str(diagram_path) if diagram_path else None,
            "preview_path": str(image_path),
            "best_time": draft.best_time,
        }

        usage = get_token_usage()
        metadata["tokens"] = usage.to_dict()
        metadata["est_cost_usd"] = round(usage.total_tokens * 0.000005, 4)

        meta_path = Path("logs") / f"{run_id}_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Metadata saved: %s", meta_path)
        log.info("Draft created [%s]: %d tokens, est cost $%.4f",
                 run_id, usage.total_tokens, usage.total_tokens * 0.000005)
        return draft, image_path
    except Exception:
        log.exception("Draft creation failed")
        raise
    finally:
        detach_file_handler()


def approve_draft(post_id: str) -> bool:
    return _set_status(post_id, "approve")


def reject_draft(post_id: str) -> bool:
    return _set_status(post_id, "reject")


def _set_status(post_id: str, action: str) -> bool:
    db = PostsDB()
    try:
        ok = getattr(db, action)(post_id)
        if ok:
            log.info("%sd draft %s", action.capitalize(), post_id)
        return ok
    finally:
        db.close()


def _load_post(post_id: str, action: str) -> dict[str, object] | None:
    db = PostsDB()
    try:
        post = db.get_post(post_id)
    finally:
        db.close()
    if not post:
        log.warning("Post %s not found for %s", post_id, action)
    return post


async def edit_draft(post_id: str, instructions: str) -> tuple[PostDraft, Path] | None:
    """Revise an existing draft with edit instructions, re-render preview."""
    post = _load_post(post_id, "editing")
    if not post:
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

    diagram_path = _generate_diagram(post_id, revised.image_suggestion, revised.category)
    image_path = _render_preview(revised.hook, revised.body, diagram_path)
    log.info("Edited draft %s", post_id)
    return revised, image_path


async def regenerate_draft(post_id: str) -> tuple[PostDraft, Path] | None:
    """Re-generate a draft from the same topic, replacing content in DB."""
    post = _load_post(post_id, "regeneration")
    if not post:
        return None

    source = post.get("source", {})
    topic = str(source.get("title", "")) if isinstance(source, dict) else ""
    log.info("Regenerating draft %s with topic=%s", post_id, topic or "(original)")

    draft = await generate_single_draft(topic)
    if not draft:
        return None

    draft.id = post_id
    draft.created_at = str(post.get("created_at", ""))

    db = PostsDB()
    try:
        db.save_draft(draft)
    finally:
        db.close()

    diagram_path = _generate_diagram(post_id, draft.image_suggestion, draft.category)
    image_path = _render_preview(draft.hook, draft.body, diagram_path)

    log.info("Regenerated draft %s", post_id)
    return draft, image_path


def regenerate_preview(post_id: str) -> Path | None:
    """Re-render the preview image for an existing draft."""
    post = _load_post(post_id, "preview regeneration")
    if not post:
        return None

    diagram_path = _generate_diagram(
        post_id, str(post.get("image_suggestion", "")), str(post.get("category", ""))
    )
    image_path = _render_preview(str(post["hook"]), str(post["body"]), diagram_path)
    log.info("Preview regenerated for %s: %s", post_id, image_path)
    return image_path


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
