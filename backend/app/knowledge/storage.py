from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.knowledge.models import ProjectMetadata, ProjectKnowledge


def _slug(repo_url: str) -> str:
    """
    Derive a slug from the last path segment of a repo URL.
    Non-alphanumeric characters are replaced with '-', lowercased,
    and leading/trailing '-' are stripped.
    """
    last_segment = repo_url.rstrip("/").rsplit("/", 1)[-1]
    # strip common .git suffix if present
    last_segment = re.sub(r"\.git$", "", last_segment)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", last_segment).strip("-").lower()
    return slug or "project"


class ProjectStorage:
    """
    Filesystem-backed storage for CodeAtlas project knowledge.

    Layout::

        <base_path>/
            <project_id>/
                metadata.json
                knowledge.json
                repository/     ← cloned git repo lives here
    """

    def __init__(self, base_path: Path) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # --- project lifecycle ---

    def create_project(self, repo_url: str) -> ProjectMetadata:
        """
        Create a new project record, write metadata.json, return metadata.
        project_id is derived from the repo name + a short UUID suffix.
        """
        suffix = uuid.uuid4().hex[:8]
        project_id = f"{_slug(repo_url)}-{suffix}"

        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        metadata = ProjectMetadata(
            project_id=project_id,
            name=_slug(repo_url),
            created_at=datetime.now(timezone.utc),
            status="pending",
        )
        self._write_metadata(metadata)
        return metadata

    def get_project(self, project_id: str) -> ProjectMetadata | None:
        """Return metadata for the given project, or None if not found."""
        path = self.get_project_dir(project_id) / "metadata.json"
        if not path.exists():
            return None
        return ProjectMetadata.model_validate_json(path.read_text())

    def update_project(self, metadata: ProjectMetadata) -> None:
        """Overwrite metadata.json for the project."""
        self._write_metadata(metadata)

    def list_projects(self) -> list[ProjectMetadata]:
        """Return all projects sorted by created_at descending."""
        results: list[ProjectMetadata] = []
        for entry in self.base_path.iterdir():
            if not entry.is_dir():
                continue
            meta_path = entry / "metadata.json"
            if not meta_path.exists():
                continue
            try:
                results.append(ProjectMetadata.model_validate_json(meta_path.read_text()))
            except Exception:
                continue
        results.sort(key=lambda m: m.created_at, reverse=True)
        return results

    # --- knowledge read/write ---

    def save_knowledge(self, project_id: str, knowledge: ProjectKnowledge) -> None:
        """Write knowledge.json for the project."""
        path = self.get_project_dir(project_id) / "knowledge.json"
        path.write_text(knowledge.model_dump_json())

    def load_knowledge(self, project_id: str) -> ProjectKnowledge | None:
        """Load knowledge.json, return None if not found."""
        path = self.get_project_dir(project_id) / "knowledge.json"
        if not path.exists():
            return None
        return ProjectKnowledge.model_validate_json(path.read_text())

    # --- path helpers ---

    def get_project_dir(self, project_id: str) -> Path:
        """Return path to the project directory."""
        return self.base_path / project_id

    def get_clone_path(self, project_id: str) -> Path:
        """Return path where the repository should be cloned."""
        return self.base_path / project_id / "repository"

    # --- internal helpers ---

    def _write_metadata(self, metadata: ProjectMetadata) -> None:
        path = self.get_project_dir(metadata.project_id) / "metadata.json"
        path.write_text(metadata.model_dump_json())
