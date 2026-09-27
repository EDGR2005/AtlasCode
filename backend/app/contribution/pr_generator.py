"""
PR + Commit Generator — Sprint 5

Generates a conventional commit message suggestion and a PR draft markdown
string. Never calls the GitHub API or pushes anything.
"""
from __future__ import annotations

from app.knowledge.models import SessionMetrics

_TYPE_MAP = {
    "bug": "fix",
    "docs": "docs",
    "feature": "feat",
    "refactor": "refactor",
}


def generate_commit_message(
    issue_number: int,
    issue_title: str,
    issue_type: str = "unknown",
) -> str:
    """
    Generate a conventional commit message suggestion.
    Example: fix(auth): reject expired tokens in validate_token()

    Closes #123
    """
    commit_type = _TYPE_MAP.get(issue_type, "chore")
    # Derive a short description from the title
    short = issue_title.strip() if issue_title else f"address issue #{issue_number}"
    # Truncate to ~72 chars total
    header = f"{commit_type}: {short}"
    if len(header) > 72:
        header = header[:69] + "..."
    return f"{header}\n\nCloses #{issue_number}"


def generate_pr_draft(
    issue_number: int,
    issue_title: str,
    session: SessionMetrics,
) -> str:
    """
    Generate a pull request description in markdown format.
    Does NOT call the GitHub API or create anything remotely.
    """
    tests_line = (
        f"- {session.tests_passed} test(s) passed, {session.tests_failed} failed"
        if session.tests_run > 0
        else "- No test suite detected"
    )
    attempts_line = (
        f"- Verification attempts: {len(session.attempts)}"
        if session.attempts
        else ""
    )

    return f"""\
## Summary

<!-- One-sentence summary of the change -->
Addresses issue #{issue_number}: {issue_title}

## Problem

<!-- Describe what the issue reported -->

## Changes

<!-- List each changed file and what was modified -->
- Branch: `{session.branch_name}`
- Files modified: {session.files_modified}

## Testing

{tests_line}
{attempts_line}

## Related Issue

Closes #{issue_number}
""".strip()
