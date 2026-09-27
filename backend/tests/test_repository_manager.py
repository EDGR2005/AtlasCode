"""
Tests for contribution.repository_manager.

All tests are fully offline — they use tmp_path + git.Repo.init() to create
real local git repositories without any network calls.
"""
from __future__ import annotations

from pathlib import Path

import git
import pytest

from app.contribution.repository_manager import (
    commit_all,
    create_branch,
    get_current_branch,
    get_diff,
    get_repo,
    get_status,
    make_branch_name,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _init_repo(path: Path) -> git.Repo:
    """Initialise a bare-minimum git repo with one commit so HEAD is valid."""
    repo = git.Repo.init(str(path))
    # Configure identity so commits work in all environments
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    # Create an initial commit
    readme = path / "README.md"
    readme.write_text("# Test repo\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo


@pytest.fixture()
def repo_path(tmp_path: Path) -> Path:
    """Return the path of a freshly initialised git repo."""
    _init_repo(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# make_branch_name
# ---------------------------------------------------------------------------

def test_make_branch_name_basic():
    assert make_branch_name(42, "Fix expired token") == "atlas/42-fix-expired-token"


def test_make_branch_name_special_chars():
    name = make_branch_name(7, "  Handle: NULL / empty values!  ")
    assert name.startswith("atlas/7-")
    assert " " not in name
    assert "/" not in name[len("atlas/7-"):]


def test_make_branch_name_long_title():
    long_title = "a" * 200
    name = make_branch_name(1, long_title)
    # slug portion must not exceed 50 chars
    slug = name[len("atlas/1-"):]
    assert len(slug) <= 50


def test_make_branch_name_empty_title():
    name = make_branch_name(99, "   ")
    assert name.startswith("atlas/99-")


# ---------------------------------------------------------------------------
# get_repo
# ---------------------------------------------------------------------------

def test_get_repo_returns_repo_instance(repo_path: Path):
    repo = get_repo(repo_path)
    assert isinstance(repo, git.Repo)


def test_get_repo_invalid_path_raises(tmp_path: Path):
    with pytest.raises(Exception):
        get_repo(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# create_branch / get_current_branch
# ---------------------------------------------------------------------------

def test_create_branch_and_checkout(repo_path: Path):
    create_branch(repo_path, "atlas/1-test-feature")
    assert get_current_branch(repo_path) == "atlas/1-test-feature"


def test_create_branch_duplicate_raises(repo_path: Path):
    create_branch(repo_path, "atlas/2-duplicate")
    with pytest.raises(Exception):
        create_branch(repo_path, "atlas/2-duplicate")


def test_get_current_branch_initial(repo_path: Path):
    branch = get_current_branch(repo_path)
    # fresh repo may be on "main" or "master" depending on git config
    assert isinstance(branch, str)
    assert len(branch) > 0


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

def test_get_status_clean(repo_path: Path):
    assert get_status(repo_path) == []


def test_get_status_modified_file(repo_path: Path):
    (repo_path / "README.md").write_text("# Modified\n")
    changed = get_status(repo_path)
    assert "README.md" in changed


def test_get_status_untracked_file(repo_path: Path):
    (repo_path / "new_file.py").write_text("x = 1\n")
    changed = get_status(repo_path)
    assert "new_file.py" in changed


def test_get_status_multiple_files(repo_path: Path):
    (repo_path / "README.md").write_text("# Changed\n")
    (repo_path / "other.txt").write_text("hello\n")
    changed = get_status(repo_path)
    assert "README.md" in changed
    assert "other.txt" in changed


# ---------------------------------------------------------------------------
# get_diff
# ---------------------------------------------------------------------------

def test_get_diff_clean_is_empty(repo_path: Path):
    assert get_diff(repo_path) == ""


def test_get_diff_shows_changes(repo_path: Path):
    (repo_path / "README.md").write_text("# Changed content\n")
    diff = get_diff(repo_path)
    assert "README.md" in diff
    assert "Changed content" in diff


def test_get_diff_returns_string(repo_path: Path):
    diff = get_diff(repo_path)
    assert isinstance(diff, str)


# ---------------------------------------------------------------------------
# commit_all
# ---------------------------------------------------------------------------

def test_commit_all_clean_raises(repo_path: Path):
    with pytest.raises(ValueError, match="Nothing to commit"):
        commit_all(repo_path, "empty commit")


def test_commit_all_modified_file(repo_path: Path):
    (repo_path / "README.md").write_text("# Updated\n")
    sha = commit_all(repo_path, "update readme")
    assert isinstance(sha, str)
    assert len(sha) == 40


def test_commit_all_returns_new_sha(repo_path: Path):
    repo = get_repo(repo_path)
    original_sha = repo.head.commit.hexsha

    (repo_path / "README.md").write_text("# New content\n")
    new_sha = commit_all(repo_path, "second commit")
    assert new_sha != original_sha


def test_commit_all_message_recorded(repo_path: Path):
    (repo_path / "README.md").write_text("# Commit message test\n")
    commit_all(repo_path, "my commit message")
    repo = get_repo(repo_path)
    assert repo.head.commit.message.strip() == "my commit message"


def test_commit_all_does_not_add_untracked(repo_path: Path):
    """commit_all uses git add -u — untracked files must NOT be staged."""
    (repo_path / "untracked.py").write_text("x = 1\n")
    with pytest.raises(ValueError, match="Nothing to commit"):
        commit_all(repo_path, "should fail")


# ---------------------------------------------------------------------------
# Integration: full branch workflow
# ---------------------------------------------------------------------------

def test_full_branch_workflow(repo_path: Path):
    """Create branch → modify file → commit → verify diff is empty afterwards."""
    create_branch(repo_path, "atlas/10-full-flow")
    assert get_current_branch(repo_path) == "atlas/10-full-flow"

    (repo_path / "README.md").write_text("# Phase 2 change\n")
    assert get_status(repo_path) != []
    assert "README.md" in get_diff(repo_path)

    sha = commit_all(repo_path, "feat: phase 2 change")
    assert len(sha) == 40

    # After commit the working tree should be clean
    assert get_status(repo_path) == []
    assert get_diff(repo_path) == ""
