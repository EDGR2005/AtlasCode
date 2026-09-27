"""
Tests for contribution.plan_generator.
All offline.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.contribution.plan_generator import generate_plan, _detect_test_hint
from app.knowledge.models import (
    IssueAnalysis,
    ProjectKnowledge,
    ProjectMetadata,
    RepositoryInfo,
    TechnologyDetection,
    Dependency,
)


def _knowledge(techs: list[str] | None = None, deps: list[str] | None = None) -> ProjectKnowledge:
    tech_list = [
        TechnologyDetection(name=t, source="package.json", confidence=1.0)
        for t in (techs or [])
    ]
    dep_list = [
        Dependency(name=d, version=None, ecosystem="pypi", source="requirements.txt")
        for d in (deps or [])
    ]
    return ProjectKnowledge(
        metadata=ProjectMetadata(
            project_id="p1",
            name="test",
            created_at=datetime.now(timezone.utc),
            status="ready",
        ),
        repository=RepositoryInfo(url="https://github.com/o/r", clone_path="/tmp"),
        technologies=tech_list,
        dependencies=dep_list,
    )


def _analysis(issue_number: int = 1, issue_type: str = "bug") -> IssueAnalysis:
    return IssueAnalysis(
        issue_number=issue_number,
        title="Test issue",
        type=issue_type,
        scope="small",
    )


def _issue(number: int = 1, title: str = "Fix something") -> dict:
    return {"number": number, "title": title, "body": ""}


# ---------------------------------------------------------------------------
# generate_plan
# ---------------------------------------------------------------------------

def test_generate_plan_returns_plan():
    plan = generate_plan(_issue(), _analysis(), [], _knowledge())
    assert plan.issue_number == 1
    assert isinstance(plan.steps, list)
    assert len(plan.steps) > 0


def test_generate_plan_not_approved_by_default():
    plan = generate_plan(_issue(), _analysis(), [], _knowledge())
    assert plan.approved is False


def test_generate_plan_branch_name_format():
    plan = generate_plan(_issue(number=42, title="Fix auth bug"), _analysis(42), [], _knowledge())
    assert plan.branch_name.startswith("atlas/42-")


def test_generate_plan_steps_are_strings():
    plan = generate_plan(_issue(), _analysis(), [], _knowledge())
    for step in plan.steps:
        assert isinstance(step.description, str)
        assert len(step.description) > 10


def test_generate_plan_steps_sequential_index():
    plan = generate_plan(_issue(), _analysis(), [], _knowledge())
    for i, step in enumerate(plan.steps, start=1):
        assert step.index == i


def test_generate_plan_includes_reproduction_step_for_bug():
    plan = generate_plan(_issue(), _analysis(issue_type="bug"), [], _knowledge())
    descriptions = [s.description.lower() for s in plan.steps]
    assert any("test" in d and ("reproduce" in d or "fail" in d) for d in descriptions)


def test_generate_plan_no_reproduction_step_for_docs():
    plan = generate_plan(_issue(), _analysis(issue_type="docs"), [], _knowledge())
    descriptions = [s.description.lower() for s in plan.steps]
    assert not any("reproduce" in d for d in descriptions)


def test_generate_plan_relevant_files_appear_in_steps():
    from app.knowledge.models import RelevantFile
    rf = RelevantFile(path="app/auth.py", reason="matched", inferred=True)
    plan = generate_plan(_issue(), _analysis(), [rf], _knowledge())
    all_text = " ".join(s.description for s in plan.steps)
    assert "app/auth.py" in all_text


# ---------------------------------------------------------------------------
# _detect_test_hint
# ---------------------------------------------------------------------------

def test_detect_pytest():
    k = _knowledge(techs=["Python"], deps=["pytest"])
    assert _detect_test_hint(k) == "pytest"


def test_detect_unittest_fallback():
    k = _knowledge(techs=["Python"])
    assert "unittest" in _detect_test_hint(k)


def test_detect_npm():
    k = _knowledge(techs=["Node.js"])
    assert _detect_test_hint(k) == "npm test"


def test_detect_cargo():
    k = _knowledge(techs=["Rust"])
    assert _detect_test_hint(k) == "cargo test"


def test_detect_go():
    k = _knowledge(techs=["Go"])
    assert _detect_test_hint(k) == "go test ./..."


def test_detect_unknown():
    k = _knowledge()
    assert "test suite" in _detect_test_hint(k)
