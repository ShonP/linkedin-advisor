"""Tool: read a GitHub repo's README, structure, and key files."""

from __future__ import annotations

import base64
import json
import subprocess

from agent_framework import tool

from advisor.log import log

_KEY_FILES = [
    "README.md",
    "pyproject.toml",
    "package.json",
    ".github/copilot-instructions.md",
    "AGENTS.md",
]

_KEY_PATTERNS = [
    "pipeline",
    "workflow",
    "agent",
    "cli",
    "config",
    "model",
    "__init__",
]


def _run_gh(*args: str) -> str | None:
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        return proc.stdout if proc.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


def _read_file(repo: str, path: str) -> str | None:
    content = _run_gh("api", f"repos/{repo}/contents/{path}", "--jq", ".content")
    if content:
        try:
            return base64.b64decode(content.strip()).decode("utf-8")
        except Exception:
            return None
    return None


@tool
def read_repo(repo: str) -> str:
    """Read a GitHub repo's README, file structure, and key source files.

    Automatically reads README, config files, and source files matching
    common patterns (pipeline, workflow, agent, cli, config, model).
    Returns everything the agent needs to understand the project architecture.
    """
    result: dict[str, object] = {"repo": repo}

    # Metadata
    meta = _run_gh("api", f"repos/{repo}",
                   "--jq", "{description,language,stargazers_count,topics}")
    if meta:
        try:
            result["metadata"] = json.loads(meta)
        except json.JSONDecodeError:
            pass

    # File tree
    tree_out = _run_gh("api", f"repos/{repo}/git/trees/HEAD?recursive=1",
                       "--jq", '[.tree[] | select(.type == "blob") | .path]')
    all_files: list[str] = []
    if tree_out:
        try:
            all_files = json.loads(tree_out)
        except json.JSONDecodeError:
            pass
    result["file_tree"] = all_files

    # Auto-select files to read: key files + pattern matches
    files_to_read: list[str] = []
    for kf in _KEY_FILES:
        if kf in all_files:
            files_to_read.append(kf)

    for f in all_files:
        if f.endswith(".py") or f.endswith(".ts") or f.endswith(".js"):
            basename = f.rsplit("/", 1)[-1].replace(".py", "").replace(".ts", "").replace(".js", "")
            if any(p in basename.lower() for p in _KEY_PATTERNS):
                if f not in files_to_read:
                    files_to_read.append(f)

    # Cap at 15 files to avoid token explosion
    files_to_read = files_to_read[:15]

    # Read files
    file_contents: dict[str, str] = {}
    for fpath in files_to_read:
        content = _read_file(repo, fpath)
        if content:
            file_contents[fpath] = content[:4000]  # cap per file

    result["files_read"] = list(file_contents.keys())
    result["file_contents"] = file_contents

    log.info("Read repo %s: %d files in tree, %d files read: %s",
             repo, len(all_files), len(file_contents), ", ".join(file_contents.keys()))
    return json.dumps(result, indent=2, ensure_ascii=False)
