"""
Tests for github.issue_analyzer.
All offline — no network calls.
"""
from __future__ import annotations

import pytest

from app.github.issue_analyzer import analyze_issue


# ---------------------------------------------------------------------------
# Helpers to build minimal issue dicts
# ---------------------------------------------------------------------------

def _issue(
    number: int = 1,
    title: str = "Some issue",
    body: str = "",
    labels: list[str] | None = None,
    comments: int = 0,
    html_url: str = "https://github.com/owner/repo/issues/1",
) -> dict:
    label_objs = [{"name": lbl} for lbl in (labels or [])]
    return {
        "number": number,
        "title": title,
        "body": body,
        "labels": label_objs,
        "comments": comments,
        "html_url": html_url,
    }


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

def test_analyze_returns_issue_analysis():
    result = analyze_issue(_issue())
    assert result.issue_number == 1
    assert isinstance(result.reasons, list)
    assert isinstance(result.concerns, list)


def test_analyze_preserves_title():
    result = analyze_issue(_issue(title="Fix the login bug"))
    assert result.title == "Fix the login bug"


def test_analyze_preserves_url():
    result = analyze_issue(_issue(html_url="https://github.com/x/y/issues/5"))
    assert result.url == "https://github.com/x/y/issues/5"


# ---------------------------------------------------------------------------
# Scope estimation
# ---------------------------------------------------------------------------

def test_scope_small_from_label():
    result = analyze_issue(_issue(labels=["small"]))
    assert result.scope == "small"


def test_scope_small_from_short_body():
    result = analyze_issue(_issue(body="A short description."))
    assert result.scope == "small"


def test_scope_large_from_label():
    result = analyze_issue(_issue(labels=["breaking change"]))
    assert result.scope == "large"


def test_scope_large_from_long_body():
    result = analyze_issue(_issue(body="x " * 1500))
    assert result.scope == "large"


def test_scope_medium_from_medium_body():
    result = analyze_issue(_issue(body="x " * 400))
    assert result.scope == "medium"


def test_scope_unknown_no_body():
    result = analyze_issue(_issue(body=""))
    assert result.scope == "unknown"


# ---------------------------------------------------------------------------
# Type estimation
# ---------------------------------------------------------------------------

def test_type_bug_from_label():
    result = analyze_issue(_issue(labels=["bug"]))
    assert result.type == "bug"


def test_type_docs_from_label():
    result = analyze_issue(_issue(labels=["documentation"]))
    assert result.type == "docs"


def test_type_feature_from_label():
    result = analyze_issue(_issue(labels=["feature"]))
    assert result.type == "feature"


def test_type_bug_from_title():
    result = analyze_issue(_issue(title="Fix crash on login"))
    assert result.type == "bug"


def test_type_docs_from_title():
    result = analyze_issue(_issue(title="Update README with new examples"))
    assert result.type == "docs"


def test_type_unknown_no_signals():
    result = analyze_issue(_issue(title="Improve something", body=""))
    assert result.type == "unknown"


# ---------------------------------------------------------------------------
# Reason signals
# ---------------------------------------------------------------------------

def test_reason_for_beginner_label():
    result = analyze_issue(_issue(labels=["good first issue"]))
    assert any("good first issue" in r.lower() for r in result.reasons)


def test_reason_for_description_present():
    result = analyze_issue(_issue(body="This is a description."))
    assert any("description" in r.lower() for r in result.reasons)


def test_reason_for_reproduction_steps():
    body = "Steps to reproduce: 1. Do X. Expected: Y. Actual: Z."
    result = analyze_issue(_issue(body=body))
    assert any("reproduction" in r.lower() or "expected" in r.lower() for r in result.reasons)


def test_reason_for_comments():
    result = analyze_issue(_issue(comments=3))
    assert any("comment" in r.lower() for r in result.reasons)


# ---------------------------------------------------------------------------
# Concern signals
# ---------------------------------------------------------------------------

def test_concern_for_no_description():
    result = analyze_issue(_issue(body=""))
    assert any("no description" in c.lower() for c in result.concerns)


def test_concern_for_complexity_label():
    result = analyze_issue(_issue(labels=["breaking change"]))
    assert any("breaking" in c.lower() for c in result.concerns)


def test_concern_for_complex_body_keyword():
    result = analyze_issue(_issue(body="This requires a full architecture refactor."))
    assert any("architecture" in c.lower() or "refactor" in c.lower() for c in result.concerns)


def test_concern_for_very_long_body():
    result = analyze_issue(_issue(body="word " * 700))
    assert any("long" in c.lower() or "complex" in c.lower() for c in result.concerns)


# ---------------------------------------------------------------------------
# Labels preserved
# ---------------------------------------------------------------------------

def test_labels_preserved():
    result = analyze_issue(_issue(labels=["bug", "good first issue"]))
    assert "bug" in result.labels
    assert "good first issue" in result.labels


# ---------------------------------------------------------------------------
# No-crash on edge cases
# ---------------------------------------------------------------------------

def test_empty_issue_does_not_crash():
    result = analyze_issue({})
    assert result.issue_number == 0
    assert result.title == ""


def test_none_body_does_not_crash():
    result = analyze_issue({"number": 1, "title": "Test", "body": None, "labels": []})
    assert isinstance(result.concerns, list)
