"""
GitHub Issue Analyzer — Sprint 2

Classifies a raw GitHub issue dict into a structured IssueAnalysis.
Produces human-readable reasons (positive signals) and concerns (risk signals).
No numerical scores are ever computed or returned.
"""
from __future__ import annotations

import re

from app.knowledge.models import IssueAnalysis

# ---------------------------------------------------------------------------
# Label signal sets
# ---------------------------------------------------------------------------

_BEGINNER_LABELS = {
    "good first issue", "good-first-issue",
    "first contribution", "first-contribution",
    "beginner", "beginner friendly", "beginner-friendly",
    "easy", "starter", "up for grabs",
    "help wanted", "help-wanted",
    "documentation", "docs",
    "bug", "small", "minor", "trivial",
}

_COMPLEXITY_LABELS = {
    "breaking change", "breaking-change",
    "rfc", "architecture", "security",
    "performance", "refactor", "major",
    "needs design", "blocked",
}

# ---------------------------------------------------------------------------
# Keyword signals in title / body
# ---------------------------------------------------------------------------

_BEGINNER_TITLE_KEYWORDS = {
    "typo", "fix", "bug", "error", "crash", "wrong", "incorrect",
    "missing", "update", "add", "remove", "rename", "cleanup",
    "documentation", "docs", "readme", "comment",
}

_COMPLEXITY_BODY_KEYWORDS = {
    "architecture", "migration", "breaking", "refactor",
    "performance", "database schema", "security", "auth",
    "oauth", "design", "rewrite",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label_names(issue: dict) -> list[str]:
    return [lbl.get("name", "").lower() for lbl in issue.get("labels", [])]


def _body_text(issue: dict) -> str:
    return (issue.get("body") or "").lower()


def _title_text(issue: dict) -> str:
    return (issue.get("title") or "").lower()


def _estimate_scope(issue: dict, labels: list[str]) -> str:
    body = issue.get("body") or ""
    body_len = len(body)

    # Label-based
    small_labels = {"small", "minor", "trivial", "easy", "documentation", "docs", "typo"}
    large_labels = {"breaking change", "breaking-change", "architecture", "rfc", "major"}
    if any(lbl in small_labels for lbl in labels):
        return "small"
    if any(lbl in large_labels for lbl in labels):
        return "large"
    if not body:
        return "unknown"

    # Body length heuristic
    if body_len < 800:
        return "small"
    if body_len > 2500:
        return "large"
    return "medium"


def _estimate_type(issue: dict, labels: list[str]) -> str:
    bug_labels = {"bug", "fix", "crash", "error"}
    doc_labels = {"documentation", "docs", "readme"}
    feat_labels = {"feature", "enhancement", "feat", "request"}
    refactor_labels = {"refactor", "cleanup", "tech debt", "technical debt"}

    for lbl in labels:
        if lbl in bug_labels:
            return "bug"
        if lbl in doc_labels:
            return "docs"
        if lbl in feat_labels:
            return "feature"
        if lbl in refactor_labels:
            return "refactor"

    # Fall back to title keywords
    title = _title_text(issue)
    if any(w in title for w in ("fix", "bug", "error", "crash", "wrong")):
        return "bug"
    if any(w in title for w in ("doc", "readme", "comment", "typo")):
        return "docs"
    if any(w in title for w in ("add", "implement", "feature", "support")):
        return "feature"
    if any(w in title for w in ("refactor", "clean", "rename", "move")):
        return "refactor"

    return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_issue(issue: dict) -> IssueAnalysis:
    """
    Analyse a raw GitHub issue dict and return a structured IssueAnalysis.
    Never raises — returns a valid (possibly sparse) analysis on bad input.
    """
    labels = _label_names(issue)
    body = _body_text(issue)
    title = _title_text(issue)
    body_raw = issue.get("body") or ""
    body_len = len(body_raw)

    reasons: list[str] = []
    concerns: list[str] = []

    # --- Positive signals ---

    if any(lbl in _BEGINNER_LABELS for lbl in labels):
        matching = [lbl for lbl in labels if lbl in _BEGINNER_LABELS]
        reasons.append(f"Labelled as approachable: {', '.join(matching)}")

    if body_len > 0:
        reasons.append("Issue includes a description.")
    
    if body_len > 0 and any(w in body for w in ("expected", "actual", "reproduce", "steps to reproduce", "expected behavior")):
        reasons.append("Reproduction steps or expected vs actual behavior described.")

    if any(w in title for w in _BEGINNER_TITLE_KEYWORDS):
        reasons.append("Title suggests a focused, well-scoped change.")

    if 200 <= body_len <= 1500:
        reasons.append("Description length suggests a focused scope.")

    comment_count = issue.get("comments", 0)
    if comment_count > 0:
        reasons.append(f"Has {comment_count} comment(s) — community is engaged.")

    # --- Concern signals ---

    if not body_raw.strip():
        concerns.append("No description provided — scope is unclear.")

    if any(lbl in _COMPLEXITY_LABELS for lbl in labels):
        matching = [lbl for lbl in labels if lbl in _COMPLEXITY_LABELS]
        concerns.append(f"Labels suggest complexity: {', '.join(matching)}.")

    if any(kw in body for kw in _COMPLEXITY_BODY_KEYWORDS):
        matched = [kw for kw in _COMPLEXITY_BODY_KEYWORDS if kw in body]
        concerns.append(f"Description mentions complex topics: {', '.join(matched[:3])}.")

    if body_len > 3000:
        concerns.append("Very long description — may indicate high complexity.")

    if comment_count == 0 and body_len == 0:
        concerns.append("No description and no comments — issue may be abandoned.")

    # Count how many files / paths are referenced (rough heuristic)
    file_refs = len(re.findall(r"\b\w+\.\w{1,5}\b", body_raw))
    if file_refs > 15:
        concerns.append("References many files/paths — may touch multiple modules.")

    return IssueAnalysis(
        issue_number=issue.get("number", 0),
        title=issue.get("title", ""),
        type=_estimate_type(issue, labels),
        scope=_estimate_scope(issue, labels),
        reasons=reasons,
        concerns=concerns,
        labels=[lbl.get("name", "") for lbl in issue.get("labels", [])],
        url=issue.get("html_url", ""),
    )
