from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TechnologyDetection(BaseModel):
    name: str
    version: str | None = None
    source: str           # e.g. "package.json", "file_extension"
    confidence: float = Field(ge=0.0, le=1.0)


class Dependency(BaseModel):
    name: str
    version: str | None = None
    ecosystem: str        # e.g. "npm", "pypi", "maven", "cargo", "go"
    source: str           # manifest file path relative to repo root


class FileEntry(BaseModel):
    path: str             # relative to repo root
    size_bytes: int
    extension: str        # e.g. ".py", ".ts", "" for no extension
    is_important: bool = False   # True for manifest/config files


class Component(BaseModel):
    name: str
    path: str             # relative to repo root
    type: str = "unknown"  # "controller", "service", "module", "unknown", etc.


class Relationship(BaseModel):
    from_component: str   # component name or file path
    to_component: str
    type: str             # e.g. "imports"
    confidence: float = Field(ge=0.0, le=1.0)
    inferred: bool = True  # True = detected by heuristic; False = explicit fact


class RepositoryInfo(BaseModel):
    url: str
    default_branch: str = "main"
    commit_sha: str | None = None
    clone_path: str       # absolute path to cloned repo


class ProjectMetadata(BaseModel):
    project_id: str
    name: str
    created_at: datetime
    status: Literal["pending", "analyzing", "ready", "error"] = "pending"
    error_message: str | None = None


class ProjectKnowledge(BaseModel):
    metadata: ProjectMetadata
    repository: RepositoryInfo
    technologies: list[TechnologyDetection] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
