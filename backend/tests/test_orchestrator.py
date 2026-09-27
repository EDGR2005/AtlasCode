"""
Tests for contribution.orchestrator state machine.
All offline — no real git repos or subprocess calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import git
import pytest

from app.contribution.orchestrator import run_contribution, MAX_FIX_ATTEMPTS
from app.knowledge.models import SessionMetrics, TestResult


def _make_storage(tmp_path: Path):
    """Return a real ProjectStorage pointing at tmp_path."""
    from app.knowledge.storage import ProjectStorage
    storage = ProjectStorage(tmp_path)

    # Create a minimal project
    from app.knowledge.models import (
        ProjectMetadata, ProjectKnowledge, RepositoryInfo,
    )
    meta = ProjectMetadata(
        project_id="p1",
        name="test",
        created_at=datetime.now(timezone.utc),
        status="ready",
    )
    storage.base_path.mkdir(parents=True, exist_ok=True)
    project_dir = storage.get_project_dir("p1")
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "metadata.json").write_text(meta.model_dump_json())

    knowledge = ProjectKnowledge(
        metadata=meta,
        repository=RepositoryInfo(url="https://github.com/o/r", clone_path=str(tmp_path)),
    )
    storage.save_knowledge("p1", knowledge)
    return storage


def _init_git_repo(path: Path) -> git.Repo:
    repo = git.Repo.init(str(path))
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    (path / "README.md").write_text("hi\n")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    return repo


# ---------------------------------------------------------------------------
# State transitions — no test suite detected
# ---------------------------------------------------------------------------

def test_orchestrator_done_when_no_test_suite(tmp_path: Path):
    storage = _make_storage(tmp_path)
    clone_path = storage.get_clone_path("p1")
    clone_path.mkdir(parents=True, exist_ok=True)
    _init_git_repo(clone_path)

    with patch("app.contribution.orchestrator.detect_test_command", return_value=None):
        run_contribution("p1", 1, "atlas/1-test", storage)

    session = storage.load_session("p1")
    assert session is not None
    assert session.state == "DONE"


# ---------------------------------------------------------------------------
# State transitions — tests pass first time
# ---------------------------------------------------------------------------

def test_orchestrator_done_on_passing_tests(tmp_path: Path):
    storage = _make_storage(tmp_path)
    clone_path = storage.get_clone_path("p1")
    clone_path.mkdir(parents=True, exist_ok=True)
    _init_git_repo(clone_path)

    passing = TestResult(passed=5, failed=0)

    with patch("app.contribution.orchestrator.detect_test_command", return_value="pytest"), \
         patch("app.contribution.orchestrator.run_tests", return_value=passing):
        run_contribution("p1", 1, "atlas/1-test", storage)

    session = storage.load_session("p1")
    assert session.state == "DONE"
    assert session.tests_passed == 5
    assert len(session.attempts) == 1


# ---------------------------------------------------------------------------
# State transitions — tests fail, exhausts fix attempts
# ---------------------------------------------------------------------------

def test_orchestrator_failed_after_max_attempts(tmp_path: Path):
    storage = _make_storage(tmp_path)
    clone_path = storage.get_clone_path("p1")
    clone_path.mkdir(parents=True, exist_ok=True)
    _init_git_repo(clone_path)

    failing = TestResult(passed=0, failed=2)

    with patch("app.contribution.orchestrator.detect_test_command", return_value="pytest"), \
         patch("app.contribution.orchestrator.run_tests", return_value=failing):
        run_contribution("p1", 1, "atlas/1-test", storage)

    session = storage.load_session("p1")
    assert session.state == "FAILED"
    # The loop runs MAX_FIX_ATTEMPTS test attempts; fix_attempts is incremented
    # once per failing attempt except the last (no point fixing after cap).
    assert session.fix_attempts == MAX_FIX_ATTEMPTS - 1
    assert len(session.attempts) == MAX_FIX_ATTEMPTS


# ---------------------------------------------------------------------------
# fix_attempts cap
# ---------------------------------------------------------------------------

def test_max_fix_attempts_constant():
    assert MAX_FIX_ATTEMPTS == 3


# ---------------------------------------------------------------------------
# Branch already exists — idempotent
# ---------------------------------------------------------------------------

def test_orchestrator_handles_existing_branch(tmp_path: Path):
    storage = _make_storage(tmp_path)
    clone_path = storage.get_clone_path("p1")
    clone_path.mkdir(parents=True, exist_ok=True)
    repo = _init_git_repo(clone_path)
    # Pre-create the branch
    repo.create_head("atlas/1-test").checkout()

    passing = TestResult(passed=3, failed=0)

    with patch("app.contribution.orchestrator.detect_test_command", return_value="pytest"), \
         patch("app.contribution.orchestrator.run_tests", return_value=passing):
        run_contribution("p1", 1, "atlas/1-test", storage)

    session = storage.load_session("p1")
    assert session.state == "DONE"


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def test_orchestrator_persists_session(tmp_path: Path):
    storage = _make_storage(tmp_path)
    clone_path = storage.get_clone_path("p1")
    clone_path.mkdir(parents=True, exist_ok=True)
    _init_git_repo(clone_path)

    with patch("app.contribution.orchestrator.detect_test_command", return_value=None):
        run_contribution("p1", 42, "atlas/42-branch", storage)

    session = storage.load_session("p1")
    assert session.issue_number == 42
    assert session.branch_name == "atlas/42-branch"
    assert session.finished_at is not None
