"""CLI commands for draft management."""

from __future__ import annotations

import asyncio

import click


@click.group()
def draft() -> None:
    """Draft management commands."""


@draft.command()
@click.option("--topic", default="", help="Optional topic to focus on.")
def generate(topic: str) -> None:
    """Generate a single post draft."""
    from advisor.pipeline import create_draft

    click.echo("🚀 Generating LinkedIn post draft...")
    result = asyncio.run(create_draft(topic))
    if not result:
        click.echo("❌ No draft generated.")
        return
    draft_obj, image_path = result
    click.echo(f"✅ Draft created: {draft_obj.hook}")
    click.echo(f"   ID: {draft_obj.id}")
    click.echo(f"   Preview: {image_path}")


@draft.command("list")
@click.option(
    "--status",
    type=click.Choice(["pending", "approved", "rejected", "all"]),
    default="pending",
    show_default=True,
    help="Filter posts by status.",
)
def list_posts(status: str) -> None:
    """Show posts filtered by status."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        if status == "all":
            posts = db.list_pending() + db.list_approved() + db.list_rejected()
        else:
            posts = db.list_by_status(status)

        if not posts:
            click.echo(f"No {status} posts found.")
            return

        for post in posts:
            icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(str(post["status"]), "❓")
            click.echo(f"\n{icon} [{post['category']}] {post['hook']}")
            click.echo(f"   ID: {post['id']}")
            click.echo(f"   Created: {post['created_at']}")

        stats = db.stats()
        click.echo(
            f"\n📊 Stats: {stats['pending']} pending, {stats['approved']} approved, {stats['rejected']} rejected"
        )
    finally:
        db.close()


@draft.command()
@click.argument("draft_id")
def show(draft_id: str) -> None:
    """Show full details of a draft."""
    from advisor.db import PostsDB

    db = PostsDB()
    try:
        post = db.get_post_full(draft_id)
    finally:
        db.close()

    if not post:
        click.echo(f"❌ Draft {draft_id} not found")
        return

    icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(str(post["status"]), "❓")
    click.echo(f"\n{icon} [{post['category']}] {post['hook']}")
    click.echo(f"   ID: {post['id']}")
    click.echo(f"   Status: {post['status']}")
    click.echo(f"   Created: {post['created_at']}")
    if post.get("decided_at"):
        click.echo(f"   Decided: {post['decided_at']}")
    click.echo(f"\n{post['body']}")
    if post.get("image_suggestion"):
        click.echo(f"\n🖼️  Image: {post['image_suggestion']}")


@draft.command()
@click.argument("draft_id")
def approve(draft_id: str) -> None:
    """Approve a draft."""
    from advisor.pipeline import approve_draft

    if approve_draft(draft_id):
        click.echo(f"✅ Approved {draft_id}")
    else:
        click.echo(f"❌ Draft {draft_id} not found")


@draft.command()
@click.argument("draft_id")
def reject(draft_id: str) -> None:
    """Reject a draft."""
    from advisor.pipeline import reject_draft

    if reject_draft(draft_id):
        click.echo(f"🗑️  Rejected {draft_id}")
    else:
        click.echo(f"❌ Draft {draft_id} not found")


@draft.command()
@click.argument("draft_id")
@click.argument("instructions")
def edit(draft_id: str, instructions: str) -> None:
    """Edit a draft with instructions."""
    from advisor.pipeline import edit_draft

    result = asyncio.run(edit_draft(draft_id, instructions))
    if result:
        draft_obj, image_path = result
        click.echo(f"✏️  Edited: {draft_obj.hook}")
        click.echo(f"   Preview: {image_path}")
    else:
        click.echo(f"❌ Edit failed for {draft_id}")


@draft.command()
@click.argument("draft_id")
def regenerate(draft_id: str) -> None:
    """Re-generate a draft from the same topic."""
    from advisor.pipeline import regenerate_draft

    click.echo(f"🔄 Regenerating draft {draft_id}...")
    result = asyncio.run(regenerate_draft(draft_id))
    if result:
        draft_obj, image_path = result
        click.echo(f"✅ Regenerated: {draft_obj.hook}")
        click.echo(f"   Preview: {image_path}")
    else:
        click.echo(f"❌ Regeneration failed for {draft_id}")


@draft.command()
@click.argument("draft_id")
def preview(draft_id: str) -> None:
    """Regenerate the preview image for a draft."""
    from advisor.pipeline import regenerate_preview

    click.echo(f"🖼️  Regenerating preview for {draft_id}...")
    path = regenerate_preview(draft_id)
    if path:
        click.echo(f"✅ Preview saved: {path}")
        click.launch(str(path))
    else:
        click.echo(f"❌ Preview generation failed for {draft_id}")
