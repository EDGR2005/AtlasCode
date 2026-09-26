"""Tests for the FastAPI REST API (projects router)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_storage
from app.knowledge.models import (
    ColumnInfo,
    Component,
    DatabaseSchema,
    DbRelationship,
    Dependency,
    FileEntry,
    ProjectKnowledge,
    ProjectMetadata,
    Relationship,
    RepositoryInfo,
    TableSchema,
    TechnologyDetection,
)
from app.knowledge.storage import ProjectStorage
from app.main import app

REPO_URL = "https://github.com/owner/sample-repo"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def storage(tmp_path: Path) -> ProjectStorage:
    return ProjectStorage(tmp_path / "projects")


@pytest.fixture()
def client(storage: ProjectStorage) -> TestClient:
    """TestClient with storage dependency overridden to use tmp_path."""
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_knowledge(meta: ProjectMetadata, repo_url: str = REPO_URL) -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=meta,
        repository=RepositoryInfo(
            url=repo_url,
            clone_path="/tmp/repo",
            commit_sha="abc123",
        ),
        technologies=[
            TechnologyDetection(name="Python", source="file_extension", confidence=0.9),
        ],
        dependencies=[
            Dependency(name="fastapi", version="0.100.0", ecosystem="pypi", source="requirements.txt"),
            Dependency(name="pydantic", version="2.0.0", ecosystem="pypi", source="requirements.txt"),
        ],
        files=[
            FileEntry(path="main.py", size_bytes=512, extension=".py", is_important=True),
            FileEntry(path="README.md", size_bytes=1024, extension=".md"),
            FileEntry(path="tests/test_main.py", size_bytes=256, extension=".py"),
        ],
        components=[
            Component(name="main", path="main.py", type="module"),
        ],
        relationships=[
            Relationship(
                from_component="main",
                to_component="fastapi",
                type="imports",
                confidence=0.95,
                inferred=True,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_analyze_returns_202(client: TestClient) -> None:
    # TestClient runs background tasks synchronously, so run_pipeline will be
    # called exactly once.  We patch it to avoid any real I/O.
    with patch("app.api.projects.run_pipeline") as mock_run:
        resp = client.post("/projects/analyze", json={"repository_url": REPO_URL})

    assert resp.status_code == 202
    data = resp.json()
    assert "project_id" in data
    assert data["status"] == "analyzing"
    # Verify the pipeline was scheduled with the correct arguments
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args.args[1] == REPO_URL


def test_get_project_not_found(client: TestClient) -> None:
    resp = client.get("/projects/unknown-id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Project not found"


def test_get_project(client: TestClient, storage: ProjectStorage) -> None:
    meta = storage.create_project(REPO_URL)
    # Save knowledge so repository_url is populated in the summary
    knowledge = _make_knowledge(meta)
    storage.save_knowledge(meta.project_id, knowledge)

    resp = client.get(f"/projects/{meta.project_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == meta.project_id
    assert data["name"] == meta.name
    assert data["repository_url"] == REPO_URL
    assert data["technology_count"] == 1
    assert data["dependency_count"] == 2
    assert data["file_count"] == 3


def test_list_projects(client: TestClient, storage: ProjectStorage) -> None:
    meta1 = storage.create_project("https://github.com/owner/repo-one")
    meta2 = storage.create_project("https://github.com/owner/repo-two")

    resp = client.get("/projects/")
    assert resp.status_code == 200
    ids = {p["project_id"] for p in resp.json()}
    assert meta1.project_id in ids
    assert meta2.project_id in ids


def test_tree_analyzing(client: TestClient, storage: ProjectStorage) -> None:
    """Before knowledge.json exists the tree endpoint returns 202-like body."""
    meta = storage.create_project(REPO_URL)

    resp = client.get(f"/projects/{meta.project_id}/tree")
    # Status is 200 but body signals that analysis is in progress
    assert resp.status_code == 200
    assert resp.json() == {"status": "analyzing"}


def test_technologies_with_knowledge(
    client: TestClient, storage: ProjectStorage
) -> None:
    meta = storage.create_project(REPO_URL)
    knowledge = _make_knowledge(meta)
    storage.save_knowledge(meta.project_id, knowledge)

    resp = client.get(f"/projects/{meta.project_id}/technologies")
    assert resp.status_code == 200
    data = resp.json()
    assert "technologies" in data
    techs = data["technologies"]
    assert len(techs) == 1
    assert techs[0]["name"] == "Python"


def test_dependencies_with_knowledge(
    client: TestClient, storage: ProjectStorage
) -> None:
    meta = storage.create_project(REPO_URL)
    knowledge = _make_knowledge(meta)
    storage.save_knowledge(meta.project_id, knowledge)

    resp = client.get(f"/projects/{meta.project_id}/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    assert "dependencies" in data
    deps = data["dependencies"]
    assert len(deps) == 2
    names = {d["name"] for d in deps}
    assert names == {"fastapi", "pydantic"}


def test_architecture_with_knowledge(
    client: TestClient, storage: ProjectStorage
) -> None:
    meta = storage.create_project(REPO_URL)
    knowledge = _make_knowledge(meta)
    storage.save_knowledge(meta.project_id, knowledge)

    resp = client.get(f"/projects/{meta.project_id}/architecture")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert "relationships" in data
    assert len(data["components"]) == 1
    assert data["components"][0]["name"] == "main"
    assert len(data["relationships"]) == 1
    assert data["relationships"][0]["type"] == "imports"


def test_database_not_found(client: TestClient) -> None:
    resp = client.get("/projects/unknown-id/database")
    assert resp.status_code == 404


def test_database_analyzing(client: TestClient, storage: ProjectStorage) -> None:
    """Before knowledge.json exists the database endpoint returns analyzing body."""
    meta = storage.create_project(REPO_URL)
    resp = client.get(f"/projects/{meta.project_id}/database")
    assert resp.status_code == 200
    assert resp.json() == {"status": "analyzing"}


def test_database_empty_schema(client: TestClient, storage: ProjectStorage) -> None:
    """A project with no DB tables returns detected=False, not an error."""
    meta = storage.create_project(REPO_URL)
    knowledge = _make_knowledge(meta)
    storage.save_knowledge(meta.project_id, knowledge)

    resp = client.get(f"/projects/{meta.project_id}/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"] is False
    assert data["tables"] == []
    assert data["relationships"] == []


def test_database_with_schema(client: TestClient, storage: ProjectStorage) -> None:
    """A project with DB tables returns them correctly."""
    meta = storage.create_project(REPO_URL)
    knowledge = _make_knowledge(meta)
    knowledge.database = DatabaseSchema(
        detected=True,
        tables=[
            TableSchema(
                name="users",
                source="schema.sql",
                source_type="sql",
                confidence=1.0,
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", primary_key=True, nullable=False, source="schema.sql"),
                    ColumnInfo(name="email", data_type="VARCHAR", unique=True, source="schema.sql"),
                ],
            )
        ],
        relationships=[
            DbRelationship(
                from_table="posts",
                from_column="author_id",
                to_table="users",
                to_column="id",
                relationship_type="one_to_many",
                source="schema.sql",
                inferred=False,
            )
        ],
    )
    storage.save_knowledge(meta.project_id, knowledge)

    resp = client.get(f"/projects/{meta.project_id}/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected"] is True
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "users"
    cols = data["tables"][0]["columns"]
    pk_cols = [c for c in cols if c["primary_key"]]
    assert len(pk_cols) == 1
    assert len(data["relationships"]) == 1
    assert data["relationships"][0]["from_table"] == "posts"
