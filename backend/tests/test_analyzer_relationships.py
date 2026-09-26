"""Tests for backend/app/analyzer/relationships.py using fixture repos."""
from pathlib import Path

import pytest

from app.analyzer.files import scan_files
from app.analyzer.relationships import detect_relationships

PY_FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-python-project"
NODE_FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-node-project"


def _normalise(path: str) -> str:
    return path.replace("\\", "/")


# ── Python fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def py_rels():
    entries = scan_files(PY_FIXTURE)
    return detect_relationships(PY_FIXTURE, entries)


def test_python_main_imports_user_service(py_rels):
    found = any(
        _normalise(r.from_component).endswith("main.py")
        and _normalise(r.to_component).endswith("user_service.py")
        for r in py_rels
    )
    assert found, "Expected src/main.py → src/services/user_service.py relationship"


def test_python_main_imports_email_service(py_rels):
    found = any(
        _normalise(r.from_component).endswith("main.py")
        and _normalise(r.to_component).endswith("email_service.py")
        for r in py_rels
    )
    assert found, "Expected src/main.py → src/services/email_service.py relationship"


def test_python_all_inferred(py_rels):
    for r in py_rels:
        assert r.inferred is True


# ── Node fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def node_rels():
    entries = scan_files(NODE_FIXTURE)
    return detect_relationships(NODE_FIXTURE, entries)


def test_node_controller_imports_service(node_rels):
    found = any(
        _normalise(r.from_component).endswith("UserController.ts")
        and _normalise(r.to_component).endswith("UserService.ts")
        for r in node_rels
    )
    assert found, "Expected UserController.ts → UserService.ts relationship"


def test_node_all_inferred(node_rels):
    for r in node_rels:
        assert r.inferred is True
