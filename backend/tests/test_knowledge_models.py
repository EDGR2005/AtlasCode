from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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


def _make_project_knowledge() -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=ProjectMetadata(
            project_id="proj-001",
            name="AtlasCode",
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            status="ready",
        ),
        repository=RepositoryInfo(
            url="https://github.com/example/atlasCode",
            default_branch="main",
            commit_sha="abc123",
            clone_path="/tmp/repos/atlasCode",
        ),
        technologies=[
            TechnologyDetection(name="Python", source="file_extension", confidence=0.9)
        ],
        dependencies=[
            Dependency(name="fastapi", version="0.110.0", ecosystem="pypi", source="requirements.txt")
        ],
        files=[
            FileEntry(path="backend/app/main.py", size_bytes=512, extension=".py", is_important=True)
        ],
        components=[
            Component(name="main", path="backend/app/main.py", type="module")
        ],
        relationships=[
            Relationship(
                from_component="main",
                to_component="knowledge",
                type="imports",
                confidence=0.85,
            )
        ],
    )


def test_technology_detection_construction():
    tech = TechnologyDetection(
        name="TypeScript",
        version="5.0.0",
        source="package.json",
        confidence=0.95,
    )
    assert tech.name == "TypeScript"
    assert tech.version == "5.0.0"
    assert tech.source == "package.json"
    assert tech.confidence == 0.95


def test_technology_detection_confidence_bounds():
    with pytest.raises(ValidationError):
        TechnologyDetection(name="X", source="file", confidence=-0.1)

    with pytest.raises(ValidationError):
        TechnologyDetection(name="X", source="file", confidence=1.1)


def test_project_knowledge_json_roundtrip():
    original = _make_project_knowledge()
    json_str = original.model_dump_json()
    restored = ProjectKnowledge.model_validate_json(json_str)
    assert restored == original


def test_optional_fields_absent():
    tech = TechnologyDetection(name="Python", source="file_extension", confidence=1.0)
    assert tech.version is None


def test_relationship_inferred_default():
    rel = Relationship(
        from_component="a",
        to_component="b",
        type="imports",
        confidence=0.7,
    )
    assert rel.inferred is True


def test_project_metadata_status_validation():
    with pytest.raises(ValidationError):
        ProjectMetadata(
            project_id="p1",
            name="Test",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            status="unknown_status",
        )
