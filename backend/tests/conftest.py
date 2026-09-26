"""
Shared pytest fixtures for the CodeAtlas test suite.

These fixtures are automatically available to every test module without
an explicit import.  Heavier, test-specific fixtures live in the individual
test files.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.knowledge.models import (
    Component,
    Dependency,
    FileEntry,
    ProjectKnowledge,
    ProjectMetadata,
    Relationship,
    RepositoryInfo,
    TechnologyDetection,
)
from app.knowledge.storage import ProjectStorage

# ---------------------------------------------------------------------------
# Low-level storage fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_storage(tmp_path: Path) -> ProjectStorage:
    """A ProjectStorage backed by a fresh temporary directory."""
    return ProjectStorage(base_path=tmp_path / "projects")


# ---------------------------------------------------------------------------
# Sample knowledge objects
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_python_knowledge(tmp_storage: ProjectStorage) -> ProjectKnowledge:
    """
    A ProjectKnowledge object representing a minimal Python project,
    persisted to tmp_storage so tests that need an on-disk project can use it.
    """
    meta = ProjectMetadata(
        project_id="python-proj-test01",
        name="sample-python-project",
        created_at=datetime(2024, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
        status="ready",
    )
    knowledge = ProjectKnowledge(
        metadata=meta,
        repository=RepositoryInfo(
            url="https://github.com/example/sample-python-project",
            default_branch="main",
            commit_sha="deadbeef",
            clone_path=str(tmp_storage.get_clone_path(meta.project_id)),
        ),
        technologies=[
            TechnologyDetection(name="Python", version="3.12", source="pyproject.toml", confidence=0.99),
            TechnologyDetection(name="FastAPI", version="0.110.0", source="requirements.txt", confidence=0.95),
        ],
        dependencies=[
            Dependency(name="fastapi", version="0.110.0", ecosystem="pypi", source="requirements.txt"),
            Dependency(name="pydantic", version="2.7.0", ecosystem="pypi", source="requirements.txt"),
            Dependency(name="uvicorn", version="0.29.0", ecosystem="pypi", source="requirements.txt"),
        ],
        files=[
            FileEntry(path="pyproject.toml", size_bytes=512, extension=".toml", is_important=True),
            FileEntry(path="requirements.txt", size_bytes=128, extension=".txt", is_important=True),
            FileEntry(path="src/main.py", size_bytes=1024, extension=".py", is_important=False),
            FileEntry(path="src/utils.py", size_bytes=256, extension=".py", is_important=False),
        ],
        components=[
            Component(name="main", path="src/main.py", type="module"),
            Component(name="utils", path="src/utils.py", type="module"),
        ],
        relationships=[
            Relationship(
                from_component="main",
                to_component="utils",
                type="imports",
                confidence=0.6,
                inferred=True,
            ),
        ],
    )
    # Persist so tests can call storage.load_knowledge()
    tmp_storage.get_project_dir(meta.project_id).mkdir(parents=True, exist_ok=True)
    tmp_storage.save_knowledge(meta.project_id, knowledge)
    return knowledge


@pytest.fixture()
def sample_node_knowledge(tmp_storage: ProjectStorage) -> ProjectKnowledge:
    """
    A ProjectKnowledge object representing a minimal Node/TypeScript project,
    persisted to tmp_storage so tests that need an on-disk project can use it.
    """
    meta = ProjectMetadata(
        project_id="node-proj-test01",
        name="sample-node-project",
        created_at=datetime(2024, 3, 2, 10, 0, 0, tzinfo=timezone.utc),
        status="ready",
    )
    knowledge = ProjectKnowledge(
        metadata=meta,
        repository=RepositoryInfo(
            url="https://github.com/example/sample-node-project",
            default_branch="main",
            commit_sha="cafebabe",
            clone_path=str(tmp_storage.get_clone_path(meta.project_id)),
        ),
        technologies=[
            TechnologyDetection(name="TypeScript", version="5.4.5", source="package.json", confidence=0.99),
            TechnologyDetection(name="Node.js", version=None, source="file_extension", confidence=0.85),
        ],
        dependencies=[
            Dependency(name="express", version="4.19.2", ecosystem="npm", source="package.json"),
            Dependency(name="typescript", version="5.4.5", ecosystem="npm", source="package.json"),
            Dependency(name="lodash", version="4.17.21", ecosystem="npm", source="package.json"),
        ],
        files=[
            FileEntry(path="package.json", size_bytes=800, extension=".json", is_important=True),
            FileEntry(path="tsconfig.json", size_bytes=300, extension=".json", is_important=True),
            FileEntry(path="src/index.ts", size_bytes=2048, extension=".ts", is_important=False),
            FileEntry(path="src/helpers.ts", size_bytes=512, extension=".ts", is_important=False),
        ],
        components=[
            Component(name="index", path="src/index.ts", type="module"),
            Component(name="helpers", path="src/helpers.ts", type="module"),
        ],
        relationships=[
            Relationship(
                from_component="index",
                to_component="helpers",
                type="imports",
                confidence=0.6,
                inferred=True,
            ),
        ],
    )
    tmp_storage.get_project_dir(meta.project_id).mkdir(parents=True, exist_ok=True)
    tmp_storage.save_knowledge(meta.project_id, knowledge)
    return knowledge
