"""
CodeAtlas MCP Server.

A standalone process that exposes project knowledge via MCP stdio transport.
The filesystem `projects/` directory is the only shared medium between this
process and the FastAPI backend — no imports from app.api or app.main.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from app.knowledge.storage import ProjectStorage

# ---------------------------------------------------------------------------
# Storage singleton (module-level so tests can swap it out via the helpers)
# ---------------------------------------------------------------------------

_DEFAULT_PROJECTS_DIR = Path(__file__).resolve().parents[4] / "projects"

def _make_storage() -> ProjectStorage:
    base = Path(os.getenv("PROJECTS_DIR", str(_DEFAULT_PROJECTS_DIR)))
    return ProjectStorage(base_path=base)


# ---------------------------------------------------------------------------
# Pure helper functions — directly testable, no MCP dependency
# ---------------------------------------------------------------------------

def _get_project_overview(storage: ProjectStorage, project_id: str) -> str:
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        meta = storage.get_project(project_id)
        if meta is None:
            return f"Project '{project_id}' not found."
        return json.dumps({
            "project_id": meta.project_id,
            "name": meta.name,
            "status": meta.status,
            "created_at": meta.created_at.isoformat(),
            "technologies": [],
            "file_count": 0,
            "dependency_count": 0,
            "technology_count": 0,
            "component_count": 0,
        })

    meta = knowledge.metadata
    return json.dumps({
        "project_id": meta.project_id,
        "name": meta.name,
        "status": meta.status,
        "created_at": meta.created_at.isoformat(),
        "technologies": [t.name for t in knowledge.technologies],
        "file_count": len(knowledge.files),
        "dependency_count": len(knowledge.dependencies),
        "technology_count": len(knowledge.technologies),
        "component_count": len(knowledge.components),
    })


def _get_repository_tree(storage: ProjectStorage, project_id: str) -> str:
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return f"Project '{project_id}' not found."
    files = [
        {
            "path": f.path,
            "size_bytes": f.size_bytes,
            "extension": f.extension,
            "is_important": f.is_important,
        }
        for f in knowledge.files
    ]
    return json.dumps({"files": files})


def _get_tech_stack(storage: ProjectStorage, project_id: str) -> str:
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return f"Project '{project_id}' not found."
    techs = [
        {
            "name": t.name,
            "version": t.version,
            "source": t.source,
            "confidence": t.confidence,
        }
        for t in knowledge.technologies
    ]
    return json.dumps({"technologies": techs})


def _get_dependencies(storage: ProjectStorage, project_id: str) -> str:
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return f"Project '{project_id}' not found."
    grouped: dict[str, list[dict]] = {}
    for dep in knowledge.dependencies:
        grouped.setdefault(dep.ecosystem, []).append(
            {"name": dep.name, "version": dep.version}
        )
    return json.dumps(grouped)


def _get_architecture(storage: ProjectStorage, project_id: str) -> str:
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return f"Project '{project_id}' not found."
    components = [
        {"name": c.name, "path": c.path, "type": c.type}
        for c in knowledge.components
    ]
    relationships = [
        {
            "from": r.from_component,
            "to": r.to_component,
            "type": r.type,
            "inferred": r.inferred,
            "confidence": r.confidence,
        }
        for r in knowledge.relationships
    ]
    return json.dumps({"components": components, "relationships": relationships})


_BLOCKED_DIRS = {
    ".git", "node_modules", ".venv", "venv",
    "dist", "build", "__pycache__", ".tox",
}
_MAX_FILES = 500
_MAX_MATCHES = 50


def _search_code(storage: ProjectStorage, project_id: str, query: str) -> str:
    knowledge = storage.load_knowledge(project_id)
    if knowledge is None:
        return f"Project '{project_id}' not found."

    repo_path = storage.get_clone_path(project_id)
    if not repo_path.exists():
        return f"Repository for project '{project_id}' has not been cloned yet."

    needle = query.lower()
    matches: list[dict] = []
    files_scanned = 0
    truncated = False

    for file_path in repo_path.rglob("*"):
        if truncated:
            break
        if not file_path.is_file():
            continue
        # Skip blocked directories (any part of the relative path)
        rel = file_path.relative_to(repo_path)
        if any(part in _BLOCKED_DIRS for part in rel.parts[:-1]):
            continue

        if files_scanned >= _MAX_FILES:
            truncated = True
            break
        files_scanned += 1

        try:
            with file_path.open("r", encoding="utf-8", errors="strict") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if needle in line.lower():
                        matches.append({
                            "file": str(rel),
                            "line": lineno,
                            "text": line.rstrip("\n"),
                        })
                        if len(matches) >= _MAX_MATCHES:
                            truncated = True
                            break
        except (UnicodeDecodeError, OSError):
            # binary file or unreadable — skip
            continue

    return json.dumps({"matches": matches, "truncated": truncated})


# ---------------------------------------------------------------------------
# MCP server registration
# ---------------------------------------------------------------------------

def build_server(storage: ProjectStorage | None = None) -> MCPServer:
    """Build and return a configured MCPServer instance."""
    if storage is None:
        storage = _make_storage()

    server = MCPServer("codeatlas")

    @server.tool()
    def get_project_overview(project_id: str) -> str:
        """Return a JSON overview of a project including metadata and counts."""
        return _get_project_overview(storage, project_id)

    @server.tool()
    def get_repository_tree(project_id: str) -> str:
        """Return a JSON list of all files in the project repository."""
        return _get_repository_tree(storage, project_id)

    @server.tool()
    def get_tech_stack(project_id: str) -> str:
        """Return a JSON list of detected technologies in the project."""
        return _get_tech_stack(storage, project_id)

    @server.tool()
    def get_dependencies(project_id: str) -> str:
        """Return a JSON object of dependencies grouped by ecosystem."""
        return _get_dependencies(storage, project_id)

    @server.tool()
    def get_architecture(project_id: str) -> str:
        """Return a JSON object with components and relationships."""
        return _get_architecture(storage, project_id)

    @server.tool()
    def search_code(project_id: str, query: str) -> str:
        """Search the project source code for a query string (case-insensitive)."""
        return _search_code(storage, project_id, query)

    return server


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    server = build_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
