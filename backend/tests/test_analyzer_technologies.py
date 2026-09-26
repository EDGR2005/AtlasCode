"""Tests for backend/app/analyzer/technologies.py using fixture repos."""
from pathlib import Path

import pytest

from app.analyzer.files import scan_files
from app.analyzer.technologies import detect_technologies

PY_FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-python-project"
NODE_FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-node-project"


def _tech_names(techs) -> set[str]:
    return {t.name for t in techs}


def _find_tech(techs, name: str):
    for t in techs:
        if t.name == name:
            return t
    return None


# ── Python fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def py_techs():
    entries = scan_files(PY_FIXTURE)
    return detect_technologies(PY_FIXTURE, entries)


def test_python_detects_python(py_techs):
    assert "Python" in _tech_names(py_techs)


def test_python_detects_fastapi(py_techs):
    assert "FastAPI" in _tech_names(py_techs)


def test_python_no_invented_version_for_python(py_techs):
    tech = _find_tech(py_techs, "Python")
    assert tech is not None
    # Python interpreter version must NOT be guessed from requires-python range
    assert tech.version is None


# ── Node fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def node_techs():
    entries = scan_files(NODE_FIXTURE)
    return detect_technologies(NODE_FIXTURE, entries)


def test_node_detects_nodejs(node_techs):
    assert "Node.js" in _tech_names(node_techs)


def test_node_detects_javascript(node_techs):
    assert "JavaScript" in _tech_names(node_techs)


def test_node_detects_typescript(node_techs):
    assert "TypeScript" in _tech_names(node_techs)


def test_node_detects_express(node_techs):
    assert "Express" in _tech_names(node_techs)


def test_node_no_invented_version_for_nodejs(node_techs):
    tech = _find_tech(node_techs, "Node.js")
    assert tech is not None
    # Node.js has no version in package.json — must be None
    assert tech.version is None
