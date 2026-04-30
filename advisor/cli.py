"""CLI entry point for the LinkedIn content advisor."""

from __future__ import annotations

import asyncio

import click

from advisor.cli_draft import draft


@click.group()
def main() -> None:
    """LinkedIn Content Advisor — generate and manage LinkedIn post drafts."""


main.add_command(draft)


@main.command()
@click.option("--topic", default="", help="Optional topic to focus on.")
def generate(topic: str) -> None:
    """Generate a single post draft (alias for 'draft generate')."""
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


@main.group()
def image() -> None:
    """Image generation commands."""


@image.command("generate")
@click.argument("prompt")
@click.option("--filename", default="", help="Output filename (e.g. diagram.png).")
def image_generate(prompt: str, filename: str) -> None:
    """Generate an image from a text prompt."""
    from advisor.tools.generate_image import generate_image

    click.echo("🎨 Generating image...")
    path = generate_image(prompt, filename)
    if path:
        click.echo(f"✅ Image saved: {path}")
    else:
        click.echo("❌ Image generation failed.")


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to.")
@click.option("--port", default=8000, type=int, show_default=True, help="Port to bind to.")
def serve(host: str, port: int) -> None:
    """Start the FastAPI server with the swipe UI."""
    import uvicorn

    from advisor.api.server import app

    click.echo(f"🌐 Starting server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
