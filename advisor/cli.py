"""CLI entry point for the LinkedIn content advisor."""

from __future__ import annotations

import click

from advisor.cli_draft import draft


@click.group()
def main() -> None:
    """LinkedIn Content Advisor — generate and manage LinkedIn post drafts."""


main.add_command(draft)


@main.group()
def image() -> None:
    """Image generation commands."""


@image.command("generate")
@click.argument("prompt")
@click.option("--filename", default="", help="Output filename.")
def image_generate(prompt: str, filename: str) -> None:
    """Generate an image with gpt-image-2."""
    from advisor.tools.generate_image import generate_image

    path = generate_image(prompt, filename)
    if path:
        click.echo(f"✅ {path} ({path.stat().st_size} bytes)")
    else:
        click.echo("❌ Image generation failed")


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, type=int, show_default=True)
def serve(host: str, port: int) -> None:
    """Start the FastAPI server with the swipe UI."""
    import uvicorn

    from advisor.api.server import app

    click.echo(f"🌐 http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
