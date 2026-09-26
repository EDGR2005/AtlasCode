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


# ---------------------------------------------------------------------------
# Regression tests for path-handling bug:
# "'/core.py' is not in the subpath of '...repository'"
#
# The bug occurred when repo_path was unresolved (or passed as a relative path
# via a symlink) while os.walk's dirpath was already resolved, causing
# Path.relative_to() to raise ValueError, or when a stale absolute path was
# stored in FileEntry.path and later used in repo_path / entry.path.
# ---------------------------------------------------------------------------


def test_no_paths_are_absolute(entries):
    """No FileEntry.path must ever start with '/'. All paths must be relative."""
    for e in entries:
        assert not e.path.startswith("/"), (
            f"FileEntry.path must be relative, got absolute: {e.path!r}"
        )


def test_scan_files_via_unresolved_path(tmp_path):
    """
    scan_files must produce correct relative paths even when called with an
    unresolved path (containing '..') rather than the fully resolved form.
    Reproduces the class of error seen with Docker volume mounts where the
    storage path and the os.walk path resolve differently.
    """
    # Build a tiny repo tree
    repo = tmp_path / "myrepo"
    repo.mkdir()
    (repo / "core.py").write_text("# core")
    (repo / "utils").mkdir()
    (repo / "utils" / "helper.py").write_text("# helper")

    # Pass an unresolved path that contains '..'
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    unresolved = sibling / ".." / "myrepo"  # equivalent to tmp_path/myrepo but not resolved

    result = scan_files(unresolved)

    paths = {e.path for e in result}
    assert "core.py" in paths, f"Expected 'core.py' in {paths}"
    assert "utils/helper.py" in paths or "utils\\helper.py" in paths, (
        f"Expected 'utils/helper.py' in {paths}"
    )
    for e in result:
        assert not e.path.startswith("/"), (
            f"Path must be relative even with unresolved input, got: {e.path!r}"
        )


def test_scan_files_does_not_escape_repo_root(tmp_path):
    """
    scan_files must not return entries for files outside the repository root.
    Symlinks pointing outside the root must be silently skipped.
    """
    import os

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "inside.py").write_text("# inside")

    outside = tmp_path / "outside_secret.py"
    outside.write_text("# should not appear")

    # Create a symlink inside the repo that points outside
    try:
        os.symlink(outside, repo / "escaped.py")
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported on this platform")

    result = scan_files(repo)
    paths = {e.path for e in result}

    assert "inside.py" in paths
    # The symlink target that points outside must NOT appear
    for p in paths:
        assert "outside_secret" not in p, (
            f"scan_files returned a path that escapes the repo root: {p!r}"
        )

