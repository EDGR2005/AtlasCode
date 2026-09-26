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


class ColumnInfo(BaseModel):
    name: str
    data_type: str | None = None       # e.g. "VARCHAR", "INTEGER", "TEXT"
    primary_key: bool = False
    foreign_key: str | None = None     # "referenced_table.column" or just "referenced_table"
    nullable: bool = True
    unique: bool = False
    default: str | None = None
    source: str                        # file path where this was detected


class TableSchema(BaseModel):
    name: str                          # table / model name
    columns: list[ColumnInfo] = Field(default_factory=list)
    source: str                        # file path where this was detected
    source_type: str = "unknown"       # "sql", "sqlalchemy", "django", "prisma", "migration"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DbRelationship(BaseModel):
    from_table: str
    from_column: str | None = None
    to_table: str
    to_column: str | None = None
    relationship_type: str = "unknown"  # "one_to_many", "many_to_many", "one_to_one", "unknown"
    source: str
    inferred: bool = True


class DatabaseSchema(BaseModel):
    tables: list[TableSchema] = Field(default_factory=list)
    relationships: list[DbRelationship] = Field(default_factory=list)
    detected: bool = False             # False when no schema evidence was found


class ProjectKnowledge(BaseModel):
    metadata: ProjectMetadata
    repository: RepositoryInfo
    technologies: list[TechnologyDetection] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    database: DatabaseSchema = Field(default_factory=DatabaseSchema)
