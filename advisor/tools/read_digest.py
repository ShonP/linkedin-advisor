"""Tool: read the latest newsroom digest."""

from __future__ import annotations

from pathlib import Path

from agent_framework import tool

_DIGEST_PATH = Path.home() / "projects" / "newsroom" / "digest.md"


@tool
def read_digest() -> str:
    """Read the latest AI/tech news digest from the newsroom project.

    Returns the markdown content of the most recent digest.
    """
    if not _DIGEST_PATH.exists():
        return "No digest found at expected path."

    content = _DIGEST_PATH.read_text(encoding="utf-8")
    if len(content) > 8000:
        content = content[:8000] + "\n\n[... truncated]"
    return content
