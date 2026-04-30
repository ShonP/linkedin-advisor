"""CLI entry point for the LinkedIn content advisor."""

from __future__ import annotations

import asyncio

import click


@click.group()
def main() -> None:
    """LinkedIn Content Advisor — generate and manage LinkedIn post drafts."""


@main.command()
def generate() -> None:
    """Run the pipeline to generate new post drafts."""
    from advisor.pipeline import run_pipeline

    click.echo("🚀 Generating LinkedIn post drafts...")
    result = asyncio.run(run_pipeline())
    click.echo(f"✅ {result}")


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to.")
@click.option("--port", default=8000, type=int, show_default=True, help="Port to bind to.")
def serve(host: str, port: int) -> None:
    """Start the FastAPI server with the swipe UI."""
    import uvicorn

    from advisor.api.server import app

    click.echo(f"🌐 Starting server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


@main.command("list")
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
            status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(str(post["status"]), "❓")
            click.echo(f"\n{status_icon} [{post['category']}] {post['hook']}")
            click.echo(f"   ID: {post['id']}")
            click.echo(f"   Created: {post['created_at']}")

        stats = db.stats()
        click.echo(
            f"\n📊 Stats: {stats['pending']} pending, {stats['approved']} approved, {stats['rejected']} rejected"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
