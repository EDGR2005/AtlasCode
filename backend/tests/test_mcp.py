"""
Tests for the MCP server tool handler functions.

Strategy: we do NOT start the stdio server process. Instead we call the pure
helper functions (_get_project_overview, etc.) directly, backed by a
ProjectStorage pointed at a temporary directory.
"""
from __future__ import annotations

import json
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
from app.mcp.server import (
    _get_architecture,
    _get_dependencies,
    _get_project_overview,
    _get_repository_tree,
    _get_tech_stack,
    _search_code,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def storage(tmp_path: Path) -> ProjectStorage:
    return ProjectStorage(base_path=tmp_path)


def _make_knowledge(project_id: str = "proj-abc123") -> ProjectKnowledge:
    """Return a fully-populated ProjectKnowledge for testing."""
    return ProjectKnowledge(
        metadata=ProjectMetadata(
            project_id=project_id,
            name="my-project",
            created_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            status="ready",
        ),
        repository=RepositoryInfo(
            url="https://github.com/example/my-project",
            clone_path="/tmp/projects/proj-abc123/repository",
        ),
        technologies=[
            TechnologyDetection(name="Python", version="3.12", source="pyproject.toml", confidence=0.99),
            TechnologyDetection(name="FastAPI", version="0.110.0", source="requirements.txt", confidence=0.95),
        ],
        dependencies=[
            Dependency(name="fastapi", version="0.110.0", ecosystem="pypi", source="requirements.txt"),
            Dependency(name="express", version="4.18.0", ecosystem="npm", source="package.json"),
            Dependency(name="lodash", version="4.17.21", ecosystem="npm", source="package.json"),
        ],
        files=[
            FileEntry(path="main.py", size_bytes=1024, extension=".py", is_important=True),
            FileEntry(path="utils.py", size_bytes=512, extension=".py", is_important=False),
        ],
        components=[
            Component(name="main", path="main.py", type="module"),
        ],
        relationships=[
            Relationship(
                from_component="main",
                to_component="utils",
                type="imports",
                confidence=0.9,
                inferred=True,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Helper: persist knowledge (creates the project dir first)
# ---------------------------------------------------------------------------

def _persist(storage: ProjectStorage, knowledge: ProjectKnowledge) -> str:
    """Create the project directory then save knowledge; returns project_id."""
    pid = knowledge.metadata.project_id
    storage.get_project_dir(pid).mkdir(parents=True, exist_ok=True)
    storage.save_knowledge(pid, knowledge)
    return pid


# ---------------------------------------------------------------------------
# Tests — get_project_overview
# ---------------------------------------------------------------------------

def test_get_project_overview_found(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    result = json.loads(_get_project_overview(storage, pid))

    assert result["name"] == "my-project"
    assert result["status"] == "ready"
    assert result["file_count"] == 2
    assert result["dependency_count"] == 3
    assert result["technology_count"] == 2
    assert result["component_count"] == 1
    assert "Python" in result["technologies"]
    assert "FastAPI" in result["technologies"]


def test_get_project_overview_not_found(storage: ProjectStorage) -> None:
    result = _get_project_overview(storage, "nonexistent-id")
    assert "not found" in result.lower()
    # Must be a plain string, not JSON
    with pytest.raises((json.JSONDecodeError, ValueError)):
        json.loads(result)


# ---------------------------------------------------------------------------
# Tests — get_repository_tree
# ---------------------------------------------------------------------------

def test_get_repository_tree(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    result = json.loads(_get_repository_tree(storage, pid))

    paths = [f["path"] for f in result["files"]]
    assert "main.py" in paths
    assert "utils.py" in paths
    # Check shape of first entry
    entry = result["files"][0]
    assert "size_bytes" in entry
    assert "extension" in entry
    assert "is_important" in entry


# ---------------------------------------------------------------------------
# Tests — get_tech_stack
# ---------------------------------------------------------------------------

def test_get_tech_stack(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    result = json.loads(_get_tech_stack(storage, pid))

    names = [t["name"] for t in result["technologies"]]
    assert "Python" in names
    assert "FastAPI" in names
    # Verify full entry shape
    python_entry = next(t for t in result["technologies"] if t["name"] == "Python")
    assert python_entry["version"] == "3.12"
    assert python_entry["confidence"] == pytest.approx(0.99)


# ---------------------------------------------------------------------------
# Tests — get_dependencies
# ---------------------------------------------------------------------------

def test_get_dependencies_grouped_by_ecosystem(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    result = json.loads(_get_dependencies(storage, pid))

    assert "pypi" in result
    assert "npm" in result
    pypi_names = [d["name"] for d in result["pypi"]]
    assert "fastapi" in pypi_names
    npm_names = [d["name"] for d in result["npm"]]
    assert "express" in npm_names
    assert "lodash" in npm_names


# ---------------------------------------------------------------------------
# Tests — get_architecture
# ---------------------------------------------------------------------------

def test_get_architecture(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    result = json.loads(_get_architecture(storage, pid))

    assert "components" in result
    assert "relationships" in result
    assert result["components"][0]["name"] == "main"
    rel = result["relationships"][0]
    assert rel["from"] == "main"
    assert rel["to"] == "utils"
    assert rel["type"] == "imports"
    assert rel["inferred"] is True


# ---------------------------------------------------------------------------
# Tests — search_code
# ---------------------------------------------------------------------------

def test_search_code_finds_match(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    # Create the repository directory with a real file
    repo_dir = storage.get_clone_path(pid)
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "hello.py").write_text("def hello_world():\n    print('hello world')\n")

    result = json.loads(_search_code(storage, pid, "hello_world"))

    assert len(result["matches"]) >= 1
    match = result["matches"][0]
    assert match["file"] == "hello.py"
    assert match["line"] == 1
    assert "hello_world" in match["text"]


def test_search_code_skips_blocked_dirs(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    repo_dir = storage.get_clone_path(pid)

    # Put a matching file inside a blocked directory
    (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
    (repo_dir / ".git" / "config").write_text("secret_token = abc123\n")

    (repo_dir / "node_modules" / "pkg").mkdir(parents=True, exist_ok=True)
    (repo_dir / "node_modules" / "pkg" / "index.js").write_text("secret_token = xyz\n")

    # Put a matching file in a normal location
    (repo_dir / "app.py").write_text("# no match here\n")

    result = json.loads(_search_code(storage, pid, "secret_token"))

    files_matched = [m["file"] for m in result["matches"]]
    assert not any(".git" in f for f in files_matched)
    assert not any("node_modules" in f for f in files_matched)


def test_search_code_truncation(storage: ProjectStorage) -> None:
    knowledge = _make_knowledge()
    pid = _persist(storage, knowledge)

    repo_dir = storage.get_clone_path(pid)
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create a single file with 60 matching lines (> MAX_MATCHES of 50)
    lines = "\n".join(f"match_me line {i}" for i in range(60)) + "\n"
    (repo_dir / "big_file.py").write_text(lines)

    result = json.loads(_search_code(storage, pid, "match_me"))

    assert result["truncated"] is True
    assert len(result["matches"]) == 50
