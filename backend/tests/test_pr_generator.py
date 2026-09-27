"""
Tests for contribution.pr_generator.
All offline.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.contribution.pr_generator import generate_commit_message, generate_pr_draft
from app.knowledge.models import SessionMetrics


def _session(
    issue_number: int = 1,
    branch: str = "atlas/1-fix-bug",
    tests_passed: int = 5,
    tests_failed: int = 0,
    tests_run: int = 5,
    state: str = "DONE",
) -> SessionMetrics:
    return SessionMetrics(
        project_id="p",
        issue_number=issue_number,
        branch_name=branch,
        state=state,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        tests_run=tests_run,
        started_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# generate_commit_message
# ---------------------------------------------------------------------------

def test_commit_message_bug_type():
    msg = generate_commit_message(42, "Fix expired token validation", "bug")
    assert msg.startswith("fix:")
    assert "Closes #42" in msg


def test_commit_message_docs_type():
    msg = generate_commit_message(7, "Update README", "docs")
    assert msg.startswith("docs:")


def test_commit_message_feature_type():
    msg = generate_commit_message(3, "Add user profile endpoint", "feature")
    assert msg.startswith("feat:")


def test_commit_message_unknown_type():
    msg = generate_commit_message(1, "Something", "unknown")
    assert msg.startswith("chore:")


def test_commit_message_closes_issue():
    msg = generate_commit_message(99, "Fix crash", "bug")
    assert "Closes #99" in msg


def test_commit_message_not_too_long():
    long_title = "A" * 200
    msg = generate_commit_message(1, long_title, "bug")
    first_line = msg.split("\n")[0]
    assert len(first_line) <= 75


def test_commit_message_empty_title():
    msg = generate_commit_message(5, "", "bug")
    assert "Closes #5" in msg
    assert len(msg) > 0


# ---------------------------------------------------------------------------
# generate_pr_draft
# ---------------------------------------------------------------------------

def test_pr_draft_contains_issue_number():
    draft = generate_pr_draft(42, "Fix auth bug", _session(issue_number=42))
    assert "#42" in draft


def test_pr_draft_contains_branch():
    draft = generate_pr_draft(1, "Fix thing", _session(branch="atlas/1-fix-thing"))
    assert "atlas/1-fix-thing" in draft


def test_pr_draft_contains_test_result():
    draft = generate_pr_draft(1, "Fix", _session(tests_passed=5, tests_run=5))
    assert "5" in draft


def test_pr_draft_no_tests():
    draft = generate_pr_draft(1, "Fix", _session(tests_run=0))
    assert "No test suite" in draft


def test_pr_draft_is_markdown():
    draft = generate_pr_draft(1, "Fix", _session())
    assert "##" in draft


def test_pr_draft_closes_issue():
    draft = generate_pr_draft(7, "Fix crash", _session(issue_number=7))
    assert "Closes #7" in draft
