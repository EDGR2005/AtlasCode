"""
Tests for contribution.issue_mapper.
All offline — uses local file fixtures.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.contribution.issue_mapper import _extract_keywords, map_issue_to_files
from app.knowledge.models import (
    FileEntry,
    ProjectKnowledge,
    ProjectMetadata,
    RepositoryInfo,
    DatabaseSchema,
)
from datetime import datetime, timezone


def _make_knowledge(files: list[FileEntry]) -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=ProjectMetadata(
            project_id="test",
            name="test",
            created_at=datetime.now(timezone.utc),
            status="ready",
        ),
        repository=RepositoryInfo(url="https://github.com/owner/repo", clone_path="/tmp"),
        files=files,
    )


def _fe(path: str) -> FileEntry:
    return FileEntry(path=path, size_bytes=100, extension=Path(path).suffix)


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------

def test_extract_keywords_basic():
    kws = _extract_keywords("Fix the login authentication bug")
    assert "login" in kws
    assert "authentication" in kws
    assert "fix" in kws
    # stop words should be absent
    assert "the" not in kws


def test_extract_keywords_deduplicates():
    kws = _extract_keywords("token token token expiry")
    assert kws.count("token") == 1


def test_extract_keywords_empty():
    assert _extract_keywords("") == []


def test_extract_keywords_only_stop_words():
    result = _extract_keywords("the a an is it in on at to for")
    assert result == []


# ---------------------------------------------------------------------------
# map_issue_to_files
# ---------------------------------------------------------------------------

def test_map_returns_empty_when_no_keywords(tmp_path: Path):
    knowledge = _make_knowledge([_fe("app/main.py")])
    issue = {"number": 1, "title": "", "body": ""}
    result = map_issue_to_files(issue, knowledge, tmp_path)
    assert result == []


def test_map_matches_filename(tmp_path: Path):
    (tmp_path / "auth.py").write_text("def auth(): pass\n")
    knowledge = _make_knowledge([_fe("auth.py")])
    issue = {"number": 1, "title": "Fix auth bug", "body": "auth fails"}
    result = map_issue_to_files(issue, knowledge, tmp_path)
    assert any("auth.py" in r.path for r in result)


def test_map_matches_content(tmp_path: Path):
    (tmp_path / "utils.py").write_text("def validate_token(token): pass\n")
    knowledge = _make_knowledge([_fe("utils.py")])
    issue = {"number": 2, "title": "Token validation fails", "body": "validate_token returns wrong value"}
    result = map_issue_to_files(issue, knowledge, tmp_path)
    assert any("utils.py" in r.path for r in result)


def test_map_result_has_reason(tmp_path: Path):
    (tmp_path / "login.py").write_text("def login(): pass\n")
    knowledge = _make_knowledge([_fe("login.py")])
    issue = {"number": 3, "title": "Fix login bug", "body": ""}
    result = map_issue_to_files(issue, knowledge, tmp_path)
    if result:
        assert isinstance(result[0].reason, str)
        assert len(result[0].reason) > 0


def test_map_all_results_inferred(tmp_path: Path):
    (tmp_path / "user.py").write_text("class User: pass\n")
    knowledge = _make_knowledge([_fe("user.py")])
    issue = {"number": 4, "title": "User model issue", "body": ""}
    result = map_issue_to_files(issue, knowledge, tmp_path)
    for r in result:
        assert r.inferred is True


def test_map_max_ten_results(tmp_path: Path):
    files = []
    for i in range(20):
        fname = f"token_handler_{i}.py"
        (tmp_path / fname).write_text("def token(): pass\n")
        files.append(_fe(fname))
    knowledge = _make_knowledge(files)
    issue = {"number": 5, "title": "Token handling", "body": "token token token"}
    result = map_issue_to_files(issue, knowledge, tmp_path)
    assert len(result) <= 10
