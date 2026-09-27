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


# ---------------------------------------------------------------------------
# Phase 2 — Contribution Agent models
# ---------------------------------------------------------------------------


class IssueAnalysis(BaseModel):
    """Structured analysis of a single GitHub issue."""
    issue_number: int
    title: str
    type: str = "unknown"        # "bug" | "docs" | "feature" | "refactor" | "unknown"
    scope: str = "unknown"       # "small" | "medium" | "large" | "unknown"
    reasons: list[str] = Field(default_factory=list)   # positive approachability signals
    concerns: list[str] = Field(default_factory=list)  # risk / complexity signals
    labels: list[str] = Field(default_factory=list)
    url: str = ""


class RelevantFile(BaseModel):
    """A repository file judged relevant to an issue."""
    path: str
    reason: str
    inferred: bool = True


class ContributionStep(BaseModel):
    index: int
    description: str   # plain-language sentence


class ContributionPlan(BaseModel):
    issue_number: int
    branch_name: str
    relevant_files: list[RelevantFile] = Field(default_factory=list)
    steps: list[ContributionStep] = Field(default_factory=list)
    approved: bool = False
    repo_path: str = ""
    test_command: str = ""
    test_file_hint: str = ""


class SuiteResult(BaseModel):
    passed: int = 0
    failed: int = 0
    errors: int = 0
    output: str = ""           # raw stdout/stderr, truncated to 4000 chars
    duration_seconds: float = 0.0
    timed_out: bool = False


# Backward-compatible aliases
RunResult = SuiteResult
TestResult = SuiteResult


class VerificationAttempt(BaseModel):
    attempt: int
    result: TestResult


class SessionMetrics(BaseModel):
    project_id: str
    issue_number: int
    branch_name: str
    state: str = "IDLE"
    files_analyzed: int = 0
    files_modified: int = 0
    changed_files: list[str] = Field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    fix_attempts: int = 0
    test_runs: int = 0
    attempts: list[VerificationAttempt] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None


class ContributionSummary(BaseModel):
    issue_number: int
    issue_title: str
    branch_name: str
    commit_sha: str | None = None
    diff_stat: str = ""
    pr_draft: str = ""
    metrics: SessionMetrics | None = None
