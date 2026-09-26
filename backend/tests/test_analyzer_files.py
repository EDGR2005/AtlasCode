"""Tests for backend/app/analyzer/files.py using the sample-python-project fixture."""
from pathlib import Path

import pytest

from app.analyzer.files import scan_files

FIXTURE_PATH = Path(__file__).parent.parent.parent / "examples/fixtures/sample-python-project"


def test_fixture_exists():
    assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"


@pytest.fixture(scope="module")
def entries():
    return scan_files(FIXTURE_PATH)


def _find(entries, path_suffix: str):
    """Return the first FileEntry whose path ends with path_suffix, or None."""
    for e in entries:
        if e.path.endswith(path_suffix) or e.path == path_suffix:
            return e
    return None


def test_pyproject_toml_present_and_important(entries):
    entry = _find(entries, "pyproject.toml")
    assert entry is not None, "pyproject.toml not found in scan results"
    assert entry.is_important is True


def test_requirements_txt_present_and_important(entries):
    entry = _find(entries, "requirements.txt")
    assert entry is not None, "requirements.txt not found in scan results"
    assert entry.is_important is True


def test_main_py_present_not_important_correct_extension(entries):
    # Path may use os separator; normalise
    entry = _find(entries, "main.py")
    assert entry is not None, "src/main.py not found in scan results"
    assert entry.is_important is False
    assert entry.extension == ".py"


def test_no_git_entries(entries):
    for e in entries:
        parts = e.path.replace("\\", "/").split("/")
        assert ".git" not in parts, f"Unexpected .git entry: {e.path}"
