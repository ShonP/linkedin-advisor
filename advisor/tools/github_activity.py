"""Tool: fetch recent GitHub activity via gh CLI (includes private repos)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta

from agent_framework import tool


def _run_gh(*args: str) -> str | None:
    """Run a gh CLI command and return stdout, or None on failure."""
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        return proc.stdout if proc.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


@tool
def github_activity(username: str = "", days: int = 7) -> str:
    """Fetch recent commits, PRs, and repos for the authenticated GitHub user.

    Uses 'gh' CLI which has access to private repos and activity.
    """
    if not username:
        from advisor.config import get_settings
        username = get_settings().github_username or "ShonP"

    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: dict[str, object] = {"username": username, "recent_commits": [], "pull_requests": [], "repos": []}

    # Get recently updated repos
    repos_out = _run_gh(
        "repo", "list", username,
        "--json", "name,description,stargazerCount,primaryLanguage,url,updatedAt,isPrivate",
        "--limit", "10",
    )
    repos = json.loads(repos_out or "[]")
    results["repos"] = [
        {
            "name": r.get("name", ""),
            "description": r.get("description", ""),
            "stars": r.get("stargazerCount", 0),
            "language": (r.get("primaryLanguage") or {}).get("name", ""),
            "url": r.get("url", ""),
            "private": r.get("isPrivate", False),
        }
        for r in repos
    ]

    # Get recent commits from top 5 repos
    all_commits: list[dict[str, str]] = []
    for repo in repos[:5]:
        repo_name = f"{username}/{repo.get('name', '')}"
        commits_out = _run_gh(
            "api", f"repos/{repo_name}/commits?since={since}&per_page=5",
        )
        if commits_out:
            for c in json.loads(commits_out):
                msg = c.get("commit", {}).get("message", "").split("\n")[0]
                all_commits.append({
                    "repo": repo_name,
                    "message": msg[:120],
                    "sha": c.get("sha", "")[:8],
                    "date": c.get("commit", {}).get("author", {}).get("date", ""),
                })
    results["recent_commits"] = all_commits[:20]

    # Get recent PRs
    prs_out = _run_gh(
        "search", "prs",
        "--author", username,
        "--json", "title,url,repository,state,createdAt",
        "--limit", "10",
        "--", f"created:>={since[:10]}",
    )
    if prs_out:
        prs = json.loads(prs_out)
        results["pull_requests"] = [
            {
                "title": pr.get("title", ""),
                "url": pr.get("url", ""),
                "repo": pr.get("repository", {}).get("nameWithOwner", ""),
                "state": pr.get("state", ""),
            }
            for pr in prs[:10]
        ]

    return json.dumps(results, indent=2)
