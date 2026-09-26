from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.analyzer.pipeline import run_pipeline
from app.dependencies import get_storage
from app.knowledge.models import (
    DatabaseSchema,
    Dependency,
    FileEntry,
    TechnologyDetection,
)
from app.knowledge.storage import ProjectStorage

router = APIRouter(prefix="/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    repository_url: str


class AnalyzeResponse(BaseModel):
    project_id: str
    status: str


class ProjectSummary(BaseModel):
    project_id: str
    name: str
    status: str
    repository_url: str
    created_at: datetime
    technology_count: int = 0
    dependency_count: int = 0
    file_count: int = 0
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_summary(storage: ProjectStorage, project_id: str) -> ProjectSummary | None:
    meta = storage.get_project(project_id)
    if meta is None:
        return None

    # Defaults — may be enriched from knowledge
    repo_url = ""
    tech_count = dep_count = file_count = 0

    knowledge = storage.load_knowledge(project_id)
    if knowledge is not None:
        repo_url = knowledge.repository.url
        tech_count = len(knowledge.technologies)
        dep_count = len(knowledge.dependencies)
        file_count = len(knowledge.files)

    return ProjectSummary(
        project_id=meta.project_id,
        name=meta.name,
        status=meta.status,
        repository_url=repo_url,
        created_at=meta.created_at,
        technology_count=tech_count,
        dependency_count=dep_count,
        file_count=file_count,
        error_message=meta.error_message,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/analyze", status_code=202, response_model=AnalyzeResponse)
def analyze(
    body: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    storage: ProjectStorage = Depends(get_storage),
) -> AnalyzeResponse:
    """Kick off analysis of a repository in the background."""
    meta = storage.create_project(body.repository_url)
    background_tasks.add_task(run_pipeline, meta.project_id, body.repository_url, storage)
    return AnalyzeResponse(project_id=meta.project_id, status="analyzing")


@router.get("/", response_model=list[ProjectSummary])
def list_projects(
    storage: ProjectStorage = Depends(get_storage),
) -> list[ProjectSummary]:
    """Return all projects."""
    summaries: list[ProjectSummary] = []
    for meta in storage.list_projects():
        summary = _build_summary(storage, meta.project_id)
        if summary is not None:
            summaries.append(summary)
    return summaries


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ProjectSummary:
    """Return summary for a single project."""
    summary = _build_summary(storage, project_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return summary


@router.get("/{project_id}/tree")
def get_tree(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """Return the file tree for a project."""
    meta = storage.get_project(project_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Project not found")

    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return {"status": "analyzing"}

    return {"files": knowledge.files}


@router.get("/{project_id}/technologies")
def get_technologies(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """Return detected technologies for a project."""
    meta = storage.get_project(project_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Project not found")

    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return {"status": "analyzing"}

    return {"technologies": knowledge.technologies}


@router.get("/{project_id}/dependencies")
def get_dependencies(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """Return extracted dependencies for a project."""
    meta = storage.get_project(project_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Project not found")

    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return {"status": "analyzing"}

    return {"dependencies": knowledge.dependencies}


@router.get("/{project_id}/architecture")
def get_architecture(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """Return architecture components and relationships for a project."""
    meta = storage.get_project(project_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Project not found")

    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return {"status": "analyzing"}

    return {"components": knowledge.components, "relationships": knowledge.relationships}


@router.get("/{project_id}/database")
def get_database(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
):
    """
    Return the detected database schema for a project.
    Returns database.detected=False (not an error) when no schema was found.
    """
    meta = storage.get_project(project_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Project not found")

    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return {"status": "analyzing"}

    return knowledge.database
