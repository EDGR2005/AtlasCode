"""
GitHub REST API client — Sprint 2

Fetches open issues for a repository using the GitHub v3 REST API.
Authentication is optional: set GITHUB_TOKEN in the environment to raise
the rate limit from 60 to 5000 requests/hour.

No other GitHub API functionality is implemented here. All calls are
read-only GET requests — nothing is posted or mutated.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
_DEFAULT_TIMEOUT = 15  # seconds


def _headers(token: str | None = None) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resolved_token = token or os.getenv("GITHUB_TOKEN")
    if resolved_token:
        h["Authorization"] = f"Bearer {resolved_token}"
    return h


def get_open_issues(
    owner: str,
    repo: str,
    token: str | None = None,
    per_page: int = 30,
) -> list[dict[str, Any]]:
    """
    Fetch open issues (excluding pull requests) for owner/repo.

    Returns a list of raw GitHub issue objects (dicts).
    Raises httpx.HTTPStatusError on 4xx/5xx responses.
    Raises httpx.TimeoutException on timeout.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {"state": "open", "per_page": per_page, "page": 1}

    with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
        response = client.get(url, headers=_headers(token), params=params)
        response.raise_for_status()
        issues = response.json()

    # GitHub issues endpoint returns PRs too — filter them out
    return [i for i in issues if "pull_request" not in i]


def get_issue(
    owner: str,
    repo: str,
    issue_number: int,
    token: str | None = None,
) -> dict[str, Any]:
    """
    Fetch a single issue by number.

    Raises httpx.HTTPStatusError on 4xx/5xx responses.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}"
    with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
        response = client.get(url, headers=_headers(token))
        response.raise_for_status()
        return response.json()


def parse_owner_repo(github_url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.

    Supports:
      https://github.com/owner/repo
      https://github.com/owner/repo.git
      git@github.com:owner/repo.git

    Raises ValueError if the URL cannot be parsed.
    """
    url = github_url.strip().rstrip("/")
    # Strip .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # HTTPS format
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]

    # SSH format: git@github.com:owner/repo
    if "github.com:" in url:
        parts = url.split("github.com:")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]

    raise ValueError(f"Cannot parse owner/repo from URL: {github_url!r}")
