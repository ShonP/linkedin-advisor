"""Pipeline: collect sources → generate drafts → save to DB.

Uses the Agent Framework Functional Workflow API with @workflow/@step decorators.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from agent_framework import step, workflow

from advisor.agents.content_creator import generate_post_drafts
from advisor.db import PostsDB
from advisor.log import attach_file_handler, detach_file_handler, log, new_run_id
from advisor.middleware import get_token_usage, reset_token_usage
from advisor.models.post import PostDraft


@step
async def step_collect_sources() -> list[dict[str, str]]:
    """Collect available content sources for the agent to use."""
    log.info("Step 1/3: Collecting content sources")
    sources: list[dict[str, str]] = []

    from advisor.tools.read_digest import _DIGEST_PATH
    from advisor.tools.read_reports import _REPORTS_DIR

    if _DIGEST_PATH.exists():
        sources.append({"type": "news", "name": "newsroom digest"})
        log.info("  Found newsroom digest")

    if _REPORTS_DIR.exists():
        report_count = len(list(_REPORTS_DIR.glob("**/*.md")))
        sources.append({"type": "research", "name": f"{report_count} research reports"})
        log.info("  Found %d research reports", report_count)

    sources.append({"type": "github", "name": "GitHub activity"})
    log.info("  GitHub activity will be fetched by agent")

    return sources


@step
async def step_generate_drafts() -> list[PostDraft]:
    """Generate post drafts using the content creator agent."""
    log.info("Step 2/3: Generating post drafts via content creator agent")
    drafts = await generate_post_drafts()
    log.info("Generated %d post drafts", len(drafts))
    return drafts


@step
async def step_save_drafts(drafts: list[PostDraft]) -> int:
    """Save generated drafts to the SQLite database."""
    log.info("Step 3/3: Saving %d drafts to database", len(drafts))
    db = PostsDB()
    try:
        for draft in drafts:
            if not draft.created_at:
                draft.created_at = datetime.now(UTC).isoformat()
            db.save_draft(draft)
        log.info("Saved %d drafts to database", len(drafts))
        return len(drafts)
    finally:
        db.close()


@workflow(name="linkedin_advisor")
async def advisor_workflow(input_data: Any) -> str:
    await step_collect_sources()
    drafts = await step_generate_drafts()

    if not drafts:
        log.warning("No drafts generated")
        return "No drafts generated."

    count = await step_save_drafts(drafts)
    return f"Generated and saved {count} post drafts."


async def run_pipeline() -> str:
    """Run the full content generation pipeline."""
    run_id = new_run_id()
    reset_token_usage()
    attach_file_handler()
    log.info("Pipeline starting [%s]", run_id)

    try:
        result = await advisor_workflow.run({})
        outputs = result.get_outputs()
        summary = str(outputs[0]) if outputs else "Pipeline completed."

        usage = get_token_usage()
        log.info("Pipeline complete [%s], %d tokens", run_id, usage.total_tokens)
        return summary
    except Exception:
        log.exception("Pipeline failed")
        raise
    finally:
        detach_file_handler()


def run_pipeline_sync() -> str:
    """Synchronous wrapper for the pipeline."""
    return asyncio.run(run_pipeline())
