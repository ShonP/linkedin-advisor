"""Tool: fetch recent GitHub activity for a user via gh CLI."""

from __future__ import annotations

import json
import subprocess

from agent_framework import tool


@tool
def github_activity(username: str, days: int = 7) -> str:
    """Fetch recent commits, PRs, and repos for a GitHub user.

    Returns a JSON summary of the user's recent GitHub activity.
    """
    results: dict[str, object] = {"username": username, "commits": [], "pull_requests": [], "repos": []}

    try:
        events_cmd = [
            "gh",
            "api",
            f"users/{username}/events",
            "--jq",
            '[.[] | select(.type == "PushEvent" or .type == "PullRequestEvent")] | .[:20]',
        ]
        proc = subprocess.run(events_cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            events = json.loads(proc.stdout or "[]")
            commits = []
            prs = []
            for event in events:
                repo_name = event.get("repo", {}).get("name", "")
                if event.get("type") == "PushEvent":
                    payload_commits = event.get("payload", {}).get("commits", [])
                    for c in payload_commits[:3]:
                        commits.append(
                            {
                                "repo": repo_name,
                                "message": c.get("message", "")[:120],
                                "sha": c.get("sha", "")[:8],
                            }
                        )
                elif event.get("type") == "PullRequestEvent":
                    pr = event.get("payload", {}).get("pull_request", {})
                    prs.append(
                        {
                            "repo": repo_name,
                            "title": pr.get("title", ""),
                            "state": pr.get("state", ""),
                            "url": pr.get("html_url", ""),
                        }
                    )
            results["commits"] = commits[:10]
            results["pull_requests"] = prs[:10]
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        results["commits_error"] = "Failed to fetch events"

    try:
        repos_cmd = [
            "gh",
            "api",
            f"users/{username}/repos",
            "-f",
            "sort=updated",
            "-f",
            "per_page=5",
            "--jq",
            "[.[] | {name: .full_name, description: .description, stars: .stargazers_count, language: .language, url: .html_url}]",
        ]
        proc = subprocess.run(repos_cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            results["repos"] = json.loads(proc.stdout or "[]")
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        results["repos_error"] = "Failed to fetch repos"

    return json.dumps(results, indent=2)
