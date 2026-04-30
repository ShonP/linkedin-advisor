"""Tool: list and read deep-research reports."""

from __future__ import annotations

from pathlib import Path

from agent_framework import tool

_REPORTS_DIR = Path.home() / "projects" / "deep-research" / "reports"


@tool
def read_reports(limit: int = 5) -> str:
    """List recent deep-research reports and return their summaries.

    Scans the reports directory for markdown files and returns titles
    plus the first ~1500 chars of each report.
    """
    if not _REPORTS_DIR.exists():
        return "Reports directory not found."

    md_files = sorted(_REPORTS_DIR.glob("**/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not md_files:
        return "No research reports found."

    sections: list[str] = []
    for path in md_files[:limit]:
        content = path.read_text(encoding="utf-8")
        title_line = ""
        for line in content.splitlines():
            if line.startswith("# "):
                title_line = line.lstrip("# ").strip()
                break
        if not title_line:
            title_line = path.stem.replace("-", " ").title()

        preview = content[:1500]
        if len(content) > 1500:
            preview += "\n[... truncated]"

        sections.append(f"## {title_line}\nFile: {path.name}\n\n{preview}")

    return "\n\n---\n\n".join(sections)
