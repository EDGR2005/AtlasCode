"""Tests for backend/app/analyzer/dependencies.py using fixture repos."""
from pathlib import Path

import pytest

from app.analyzer.files import scan_files
from app.analyzer.dependencies import extract_dependencies

PY_FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-python-project"
NODE_FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-node-project"


def _dep_names(deps, ecosystem: str) -> set[str]:
    return {d.name for d in deps if d.ecosystem == ecosystem}


# ── Python fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def py_deps():
    entries = scan_files(PY_FIXTURE)
    return extract_dependencies(PY_FIXTURE, entries)


def test_python_fastapi(py_deps):
    names = _dep_names(py_deps, "pypi")
    assert "fastapi" in names


def test_python_pydantic(py_deps):
    names = _dep_names(py_deps, "pypi")
    assert "pydantic" in names


def test_python_httpx(py_deps):
    names = _dep_names(py_deps, "pypi")
    assert "httpx" in names


# ── Node fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def node_deps():
    entries = scan_files(NODE_FIXTURE)
    return extract_dependencies(NODE_FIXTURE, entries)


def test_node_express(node_deps):
    names = _dep_names(node_deps, "npm")
    assert "express" in names


def test_node_jsonwebtoken(node_deps):
    names = _dep_names(node_deps, "npm")
    assert "jsonwebtoken" in names
