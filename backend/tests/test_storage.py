"""Tests for ProjectStorage (filesystem storage layer)."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.knowledge.models import (
    ProjectKnowledge,
    ProjectMetadata,
    RepositoryInfo,
)
from app.knowledge.storage import ProjectStorage


REPO_URL = "https://github.com/owner/MyRepo"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_storage(tmp_path: Path) -> ProjectStorage:
    return ProjectStorage(base_path=tmp_path / "projects")


def _make_knowledge(metadata: ProjectMetadata, clone_path: str = "/tmp/repo") -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=metadata,
        repository=RepositoryInfo(
            url=REPO_URL,
            default_branch="main",
            commit_sha="abc123",
            clone_path=clone_path,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_project(tmp_path: Path) -> None:
    """create_project returns ProjectMetadata with status='pending'; dir and metadata.json exist."""
    storage = _make_storage(tmp_path)
    meta = storage.create_project(REPO_URL)

    assert isinstance(meta, ProjectMetadata)
    assert meta.status == "pending"
    assert meta.project_id.startswith("myrepo-")
    assert len(meta.project_id) == len("myrepo-") + 8  # slug + '-' + 8 hex chars

    project_dir = storage.get_project_dir(meta.project_id)
    assert project_dir.is_dir()
    assert (project_dir / "metadata.json").is_file()


def test_get_project_returns_none_for_unknown(tmp_path: Path) -> None:
    """get_project returns None for a project_id that doesn't exist."""
    storage = _make_storage(tmp_path)
    result = storage.get_project("does-not-exist")
    assert result is None


def test_get_project_roundtrip(tmp_path: Path) -> None:
    """create_project then get_project returns identical metadata."""
    storage = _make_storage(tmp_path)
    created = storage.create_project(REPO_URL)
    fetched = storage.get_project(created.project_id)

    assert fetched is not None
    assert fetched.project_id == created.project_id
    assert fetched.name == created.name
    assert fetched.status == created.status
    # Timestamps survive JSON round-trip (timezone-aware equality)
    assert fetched.created_at == created.created_at


def test_save_and_load_knowledge(tmp_path: Path) -> None:
    """save_knowledge then load_knowledge returns equivalent ProjectKnowledge."""
    storage = _make_storage(tmp_path)
    meta = storage.create_project(REPO_URL)
    knowledge = _make_knowledge(meta, clone_path=str(storage.get_clone_path(meta.project_id)))

    storage.save_knowledge(meta.project_id, knowledge)
    loaded = storage.load_knowledge(meta.project_id)

    assert loaded is not None
    assert loaded.metadata.project_id == meta.project_id
    assert loaded.repository.url == REPO_URL
    assert loaded.repository.commit_sha == "abc123"
    assert loaded.technologies == []
    assert loaded.dependencies == []


def test_load_knowledge_returns_none_when_missing(tmp_path: Path) -> None:
    """load_knowledge returns None when knowledge.json has not been written yet."""
    storage = _make_storage(tmp_path)
    meta = storage.create_project(REPO_URL)

    result = storage.load_knowledge(meta.project_id)
    assert result is None


def test_list_projects(tmp_path: Path) -> None:
    """list_projects returns all 3 projects sorted by created_at descending."""
    storage = _make_storage(tmp_path)

    p1 = storage.create_project("https://github.com/owner/RepoA")
    # Small sleep so timestamps differ even on fast systems
    time.sleep(0.01)
    p2 = storage.create_project("https://github.com/owner/RepoB")
    time.sleep(0.01)
    p3 = storage.create_project("https://github.com/owner/RepoC")

    projects = storage.list_projects()
    assert len(projects) == 3

    ids = [p.project_id for p in projects]
    assert p3.project_id == ids[0]
    assert p2.project_id == ids[1]
    assert p1.project_id == ids[2]


def test_get_clone_path(tmp_path: Path) -> None:
    """get_clone_path returns <base>/<project_id>/repository."""
    storage = _make_storage(tmp_path)
    meta = storage.create_project(REPO_URL)

    clone_path = storage.get_clone_path(meta.project_id)
    expected = storage.base_path / meta.project_id / "repository"
    assert clone_path == expected


def test_update_project(tmp_path: Path) -> None:
    """update_project persists field changes that can be read back."""
    storage = _make_storage(tmp_path)
    meta = storage.create_project(REPO_URL)

    assert meta.status == "pending"
    meta.status = "analyzing"
    storage.update_project(meta)

    reloaded = storage.get_project(meta.project_id)
    assert reloaded is not None
    assert reloaded.status == "analyzing"
