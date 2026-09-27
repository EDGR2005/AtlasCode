"""
Contribution Plan Generator — Sprint 3

Produces a ContributionPlan for a given issue + relevant files.
Steps are plain-language sentences — no code is written here.
"""
from __future__ import annotations

import re

from app.knowledge.models import (
    ContributionPlan,
    ContributionStep,
    IssueAnalysis,
    ProjectKnowledge,
    RelevantFile,
)
from app.contribution.repository_manager import make_branch_name


def generate_plan(
    issue: dict,
    analysis: IssueAnalysis,
    relevant_files: list[RelevantFile],
    knowledge: ProjectKnowledge,
    clone_path: Path,
) -> ContributionPlan:
    """
    Generate a step-by-step ContributionPlan.
    The plan is always human-readable and contains no generated code.
    """
    issue_number = issue.get("number", 0)
    title = issue.get("title", "")
    branch = make_branch_name(issue_number, title)

    steps = _build_steps(analysis, relevant_files, knowledge)

    test_cmd = _detect_test_hint(knowledge)
    test_files = [f for f in relevant_files if "test" in f.path.lower() or "spec" in f.path.lower()]
    test_hint = test_files[0].path if test_files else "tests/test_something.py"

    return ContributionPlan(
        issue_number=issue_number,
        branch_name=branch,
        relevant_files=relevant_files,
        steps=steps,
        approved=False,
        repo_path=str(clone_path),
        test_command=test_cmd,
        test_file_hint=test_hint,
    )

def _build_steps(
    analysis: IssueAnalysis,
    relevant_files: list[RelevantFile],
    knowledge: ProjectKnowledge,
) -> list[ContributionStep]:
    steps: list[ContributionStep] = []
    idx = 1

    # 1. Understand the issue
    steps.append(ContributionStep(
        index=idx,
        description=(
            f"Read issue #{analysis.issue_number} carefully. "
            f"Understand what is broken or missing and what the expected behaviour should be."
        ),
    ))
    idx += 1

    # 2. Explore relevant files
    if relevant_files:
        file_list = ", ".join(f.path for f in relevant_files[:4])
        steps.append(ContributionStep(
            index=idx,
            description=f"Review the likely relevant files: {file_list}.",
        ))
        idx += 1

    # 3. Locate tests
    test_files = [
        f for f in relevant_files
        if "test" in f.path.lower() or "spec" in f.path.lower()
    ]
    if test_files:
        tf_list = ", ".join(f.path for f in test_files[:3])
        steps.append(ContributionStep(
            index=idx,
            description=f"Read the existing tests related to this area: {tf_list}.",
        ))
    else:
        steps.append(ContributionStep(
            index=idx,
            description="Look for existing tests related to the affected functionality.",
        ))
    idx += 1

    # 4. Create isolated branch
    steps.append(ContributionStep(
        index=idx,
        description=(
            f"Create an isolated branch for this contribution: "
            f"atlas/{analysis.issue_number}-<short-description>."
        ),
    ))
    idx += 1

    # 5. Write a reproduction test (if issue is a bug)
    if analysis.type in ("bug", "unknown"):
        steps.append(ContributionStep(
            index=idx,
            description=(
                "Write a test that reproduces the problem described in the issue. "
                "The test should fail with the current code and pass after the fix."
            ),
        ))
        idx += 1

    # 6. Implement the fix
    steps.append(ContributionStep(
        index=idx,
        description=(
            "Implement the smallest change that fixes the issue. "
            "Follow the existing code style and do not introduce new dependencies."
        ),
    ))
    idx += 1

    # 7. Run tests
    test_cmd = _detect_test_hint(knowledge)
    steps.append(ContributionStep(
        index=idx,
        description=f"Run the test suite ({test_cmd}) and confirm all tests pass.",
    ))
    idx += 1

    # 8. Review the diff
    steps.append(ContributionStep(
        index=idx,
        description=(
            "Review the diff to make sure the changes are minimal, correct, "
            "and do not include unrelated modifications."
        ),
    ))
    idx += 1

    # 9. Commit
    steps.append(ContributionStep(
        index=idx,
        description=(
            "Commit the changes with a clear message following the conventional commits "
            "format: type(scope): short description."
        ),
    ))
    idx += 1

    return steps


def _detect_test_hint(knowledge: ProjectKnowledge) -> str:
    """Return a human-friendly test command hint based on detected technologies."""
    tech_names = {t.name.lower() for t in knowledge.technologies}
    dep_names = {d.name.lower() for d in knowledge.dependencies}

    if "python" in tech_names:
        if "pytest" in dep_names:
            return "pytest"
        return "python -m unittest"
    if "node.js" in tech_names or "javascript" in tech_names or "typescript" in tech_names:
        return "npm test"
    if "rust" in tech_names:
        return "cargo test"
    if "go" in tech_names:
        return "go test ./..."
    return "the project's test suite"
