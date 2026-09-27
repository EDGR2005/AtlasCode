"""
Tests for contribution.test_runner.
subprocess calls are mocked — no real tests are executed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest

from app.contribution.test_runner import detect_test_command, run_tests, _parse_results
from app.knowledge.models import (
    ProjectKnowledge,
    ProjectMetadata,
    RepositoryInfo,
    TechnologyDetection,
    Dependency,
)


def _knowledge(techs: list[str] | None = None, deps: list[str] | None = None) -> ProjectKnowledge:
    tech_list = [
        TechnologyDetection(name=t, source="x", confidence=1.0)
        for t in (techs or [])
    ]
    dep_list = [
        Dependency(name=d, version=None, ecosystem="pypi", source="x")
        for d in (deps or [])
    ]
    return ProjectKnowledge(
        metadata=ProjectMetadata(
            project_id="p",
            name="p",
            created_at=datetime.now(timezone.utc),
            status="ready",
        ),
        repository=RepositoryInfo(url="https://github.com/o/r", clone_path="/tmp"),
        technologies=tech_list,
        dependencies=dep_list,
    )


# ---------------------------------------------------------------------------
# detect_test_command
# ---------------------------------------------------------------------------

def test_detect_pytest_from_dep(tmp_path: Path):
    k = _knowledge(techs=["Python"], deps=["pytest"])
    assert detect_test_command(k, tmp_path) == "python -m pytest -v"


def test_detect_pytest_from_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("pytest==8.0\n")
    k = _knowledge(techs=["Python"])
    assert detect_test_command(k, tmp_path) == "python -m pytest -v"


def test_detect_unittest_fallback(tmp_path: Path):
    k = _knowledge(techs=["Python"])
    cmd = detect_test_command(k, tmp_path)
    assert "unittest" in cmd


def test_detect_npm_test(tmp_path: Path):
    import json
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "jest"}}))
    k = _knowledge(techs=["Node.js"])
    assert detect_test_command(k, tmp_path) == "npm test"


def test_detect_cargo(tmp_path: Path):
    k = _knowledge(techs=["Rust"])
    assert detect_test_command(k, tmp_path) == "cargo test"


def test_detect_go(tmp_path: Path):
    k = _knowledge(techs=["Go"])
    assert detect_test_command(k, tmp_path) == "go test ./..."


def test_detect_none_for_unknown(tmp_path: Path):
    k = _knowledge()
    assert detect_test_command(k, tmp_path) is None


# ---------------------------------------------------------------------------
# run_tests — blocked commands
# ---------------------------------------------------------------------------

def test_blocked_pip_install(tmp_path: Path):
    result = run_tests(tmp_path, "pip install requests")
    assert "Blocked" in result.output
    assert result.passed == 0


def test_blocked_npm_install(tmp_path: Path):
    result = run_tests(tmp_path, "npm install")
    assert "Blocked" in result.output


# ---------------------------------------------------------------------------
# run_tests — subprocess mock
# ---------------------------------------------------------------------------

def test_run_tests_passes(tmp_path: Path):
    mock_result = MagicMock()
    mock_result.stdout = "5 passed, 0 failed\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        result = run_tests(tmp_path, "python -m pytest -v")
    assert result.passed == 5
    assert result.failed == 0
    assert result.timed_out is False


def test_run_tests_failures(tmp_path: Path):
    mock_result = MagicMock()
    mock_result.stdout = "3 passed, 2 failed\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        result = run_tests(tmp_path, "python -m pytest -v")
    assert result.passed == 3
    assert result.failed == 2


def test_run_tests_timeout(tmp_path: Path):
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)):
        result = run_tests(tmp_path, "python -m pytest -v")
    assert result.timed_out is True


def test_run_tests_output_truncated(tmp_path: Path):
    long_output = "x" * 10000
    mock_result = MagicMock()
    mock_result.stdout = long_output
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        result = run_tests(tmp_path, "python -m pytest -v")
    assert len(result.output) <= 4000


# ---------------------------------------------------------------------------
# _parse_results
# ---------------------------------------------------------------------------

def test_parse_pytest_output():
    output = "===== 7 passed, 1 failed, 0 errors in 2.3s ====="
    p, f, e = _parse_results(output, "python -m pytest -v")
    assert p == 7
    assert f == 1
    assert e == 0


def test_parse_go_output():
    output = "--- PASS: TestFoo\n--- PASS: TestBar\n--- FAIL: TestBaz\n"
    p, f, e = _parse_results(output, "go test ./...")
    assert p == 2
    assert f == 1
