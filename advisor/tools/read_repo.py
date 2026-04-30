"""Tool: read a GitHub repo's README, structure, and key files."""

from __future__ import annotations

import json
import subprocess

from advisor.log import log


def _run_gh(*args: str) -> str | None:
    """Run a gh CLI command and return stdout."""
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        return proc.stdout if proc.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


from agent_framework import tool


@tool
def read_repo(repo: str, files: list[str] | None = None) -> str:
    """Read a repo's README, file tree, and optionally specific files.

    Args:
        repo: GitHub repo in 'owner/name' format (e.g. 'ShonP/deep-research')
        files: Optional list of file paths to read from the repo
    """
    result: dict[str, object] = {"repo": repo}

    # README
    readme = _run_gh("api", f"repos/{repo}/readme", "--jq", ".content")
    if readme:
        import base64
        try:
            result["readme"] = base64.b64decode(readme.strip()).decode("utf-8")[:5000]
        except Exception:
            result["readme"] = "(decode failed)"
    else:
        result["readme"] = "(no README)"

    # File tree (top level + key dirs)
    tree = _run_gh("api", f"repos/{repo}/git/trees/HEAD?recursive=1",
                   "--jq", '[.tree[] | select(.type == "blob") | .path] | .[:50]')
    if tree:
        try:
            result["files"] = json.loads(tree)
        except json.JSONDecodeError:
            result["files"] = []

    # Read specific files
    if files:
        file_contents: dict[str, str] = {}
        for fpath in files[:5]:  # max 5 files
            content = _run_gh("api", f"repos/{repo}/contents/{fpath}", "--jq", ".content")
            if content:
                import base64
                try:
                    decoded = base64.b64decode(content.strip()).decode("utf-8")
                    file_contents[fpath] = decoded[:3000]
                except Exception:
                    file_contents[fpath] = "(decode failed)"
        result["file_contents"] = file_contents

    # Repo metadata
    meta = _run_gh("api", f"repos/{repo}", "--jq",
                   '{description: .description, language: .language, stars: .stargazers_count, topics: .topics}')
    if meta:
        try:
            result["metadata"] = json.loads(meta)
        except json.JSONDecodeError:
            pass

    log.info("Read repo %s: %d files in tree, %d files read",
             repo, len(result.get("files", [])), len(result.get("file_contents", {})))
    return json.dumps(result, indent=2, ensure_ascii=False)
