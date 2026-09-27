"""
Contribution workflow API router — Sprint 3+

Provides all /projects/{project_id}/contribute/* endpoints.
Each endpoint operates on an already-analyzed project (status=ready).
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_storage
from app.github.client import get_open_issues, get_issue, parse_owner_repo
from app.github.issue_analyzer import analyze_issue
from app.contribution.issue_mapper import map_issue_to_files
from app.contribution.plan_generator import generate_plan
from app.knowledge.models import (
    ContributionPlan,
    ContributionSummary,
    IssueAnalysis,
    SessionMetrics,
)
from app.knowledge.storage import ProjectStorage

router = APIRouter(prefix="/projects", tags=["contribution"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    issue_number: int

class ExecuteRequest(BaseModel):
    issue_number: int
    branch_name: str

class CommitRequest(BaseModel):
    message: str
    files: list[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_ready_project(storage: ProjectStorage, project_id: str):
    """Return knowledge for a ready project or raise 404/409."""
    meta = storage.get_project(project_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Project not found")
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        raise HTTPException(status_code=409, detail="Project analysis not complete")
    return knowledge


def _require_session(storage: ProjectStorage, project_id: str) -> SessionMetrics:
    """Load session.json or raise 404."""
    session = storage.load_session(project_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No active contribution session")
    return session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{project_id}/contribute/issues", response_model=list[IssueAnalysis])
def get_contribution_issues(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> list[IssueAnalysis]:
    """Fetch open GitHub issues for the project and return suitability analyses."""
    knowledge = _require_ready_project(storage, project_id)
    try:
        owner, repo = parse_owner_repo(knowledge.repository.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        raw_issues = get_open_issues(owner, repo)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e}")

    return [analyze_issue(issue) for issue in raw_issues]


@router.post("/{project_id}/contribute/plan", response_model=ContributionPlan)
def create_contribution_plan(
    project_id: str,
    body: PlanRequest,
    storage: ProjectStorage = Depends(get_storage),
) -> ContributionPlan:
    """
    Generate a contribution plan for a specific issue.
    Does NOT create a branch or write any code.
    """
    knowledge = _require_ready_project(storage, project_id)
    try:
        owner, repo = parse_owner_repo(knowledge.repository.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        raw_issue = get_issue(owner, repo, body.issue_number)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e}")

    analysis = analyze_issue(raw_issue)
    clone_path = storage.get_clone_path(project_id)
    relevant_files = map_issue_to_files(raw_issue, knowledge, clone_path)
    plan = generate_plan(raw_issue, analysis, relevant_files, knowledge, clone_path)

    return plan


@router.post("/{project_id}/contribute/execute")
def execute_contribution(
    project_id: str,
    body: ExecuteRequest,
    storage: ProjectStorage = Depends(get_storage),
):
    """
    Start the contribution loop (branch -> guiding).
    Returns immediately with the session state.
    """
    knowledge = _require_ready_project(storage, project_id)
    clone_path = storage.get_clone_path(project_id)
    if not clone_path.exists():
        raise HTTPException(status_code=409, detail="Repository not cloned")

    from app.contribution.orchestrator import start_contribution
    session = start_contribution(
        project_id=project_id,
        issue_number=body.issue_number,
        branch_name=body.branch_name,
        storage=storage,
    )
    return session

@router.post("/{project_id}/contribute/run-tests", response_model=SessionMetrics)
def run_contribution_tests(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> SessionMetrics:
    """Run the test suite once. User triggers this when ready."""
    _require_ready_project(storage, project_id)
    from app.contribution.orchestrator import run_tests_for_user
    try:
        session = run_tests_for_user(project_id, storage)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/contribute/changed-files")
def get_changed_files(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """List files the user has modified in the working tree."""
    _require_ready_project(storage, project_id)
    clone_path = storage.get_clone_path(project_id)
    if not clone_path.exists():
        raise HTTPException(status_code=409, detail="Repository not cloned")
    
    from app.contribution.repository_manager import get_status
    return {"changed_files": get_status(clone_path)}


@router.get("/{project_id}/contribute/status", response_model=SessionMetrics)
def get_contribution_status(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> SessionMetrics:
    """Return the current orchestrator state and test attempt history."""
    return _require_session(storage, project_id)


@router.get("/{project_id}/contribute/diff")
def get_contribution_diff(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """Return the unified diff of the current working tree vs HEAD."""
    _require_ready_project(storage, project_id)
    clone_path = storage.get_clone_path(project_id)
    if not clone_path.exists():
        raise HTTPException(status_code=409, detail="Repository not cloned")

    from app.contribution.repository_manager import get_diff
    return {"diff": get_diff(clone_path)}


@router.post("/{project_id}/contribute/commit")
def commit_contribution(
    project_id: str,
    body: CommitRequest,
    storage: ProjectStorage = Depends(get_storage),
):
    """
    Stage all tracked changes and create a commit.
    Requires explicit user call — never automatic.
    """
    _require_ready_project(storage, project_id)
    clone_path = storage.get_clone_path(project_id)
    if not clone_path.exists():
        raise HTTPException(status_code=409, detail="Repository not cloned")

    from app.contribution.repository_manager import commit_selected
    try:
        sha = commit_selected(clone_path, body.message, body.files)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"sha": sha}


@router.get("/{project_id}/contribute/summary", response_model=ContributionSummary)
def get_contribution_summary(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ContributionSummary:
    """Return the full contribution summary when the session is DONE."""
    session = _require_session(storage, project_id)
    if session.state not in ("DONE", "FAILED"):
        raise HTTPException(status_code=409, detail="Contribution session not finished yet")

    knowledge = _require_ready_project(storage, project_id)

    from app.contribution.pr_generator import generate_pr_draft, generate_commit_message
    from app.contribution.repository_manager import get_diff
    clone_path = storage.get_clone_path(project_id)
    diff = get_diff(clone_path) if clone_path.exists() else ""

    # Build a minimal diff stat line
    added = diff.count("\n+") - diff.count("\n+++")
    removed = diff.count("\n-") - diff.count("\n---")
    files_changed = diff.count("\ndiff --git")
    diff_stat = f"{files_changed} file(s) changed, {added} insertion(s), {removed} deletion(s)"

    # Try to get issue title from GitHub
    issue_title = ""
    try:
        from app.github.client import parse_owner_repo, get_issue
        owner, repo = parse_owner_repo(knowledge.repository.url)
        raw_issue = get_issue(owner, repo, session.issue_number)
        issue_title = raw_issue.get("title", "")
    except Exception:
        pass

    pr_draft = generate_pr_draft(session.issue_number, issue_title, session)
    commit_msg = generate_commit_message(session.issue_number, issue_title)

    return ContributionSummary(
        issue_number=session.issue_number,
        issue_title=issue_title,
        branch_name=session.branch_name,
        commit_sha=None,
        diff_stat=diff_stat,
        pr_draft=pr_draft,
        metrics=session,
    )


@router.get("/{project_id}/contribute/pr-draft")
def get_pr_draft(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """
    Return a PR draft as markdown. Does NOT call the GitHub API or push anything.
    """
    session = _require_session(storage, project_id)
    knowledge = _require_ready_project(storage, project_id)

    issue_title = ""
    try:
        from app.github.client import parse_owner_repo, get_issue
        owner, repo = parse_owner_repo(knowledge.repository.url)
        raw_issue = get_issue(owner, repo, session.issue_number)
        issue_title = raw_issue.get("title", "")
    except Exception:
        pass

    from app.contribution.pr_generator import generate_pr_draft
    return {"markdown": generate_pr_draft(session.issue_number, issue_title, session)}
