from __future__ import annotations

import re
from pathlib import Path

from app.knowledge.models import FileEntry, Relationship

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv",
    "dist", "build", "__pycache__", ".tox",
}

_PY_IMPORT = re.compile(r"^import\s+(\S+)", re.MULTILINE)
_PY_FROM = re.compile(r"^from\s+(\S+)\s+import", re.MULTILINE)
_TS_IMPORT = re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""")


def _is_skipped(path_str: str) -> bool:
    parts = path_str.replace("\\", "/").split("/")
    return any(part in SKIP_DIRS for part in parts)


def _module_to_file(module: str, repo_path: Path) -> str | None:
    """
    Convert a Python dotted module path to a file path relative to repo root.
    Checks both <module_path>.py and <module_path>/__init__.py against the repo.
    repo_path must already be resolved by the caller.
    """
    rel = module.replace(".", "/")
    # Build candidate paths directly from the relative segment — never call
    # relative_to() on a candidate that was just constructed from repo_path,
    # because that produces a relative path (e.g. "core.py") which, when
    # joined again, works fine; but if repo_path were unresolved it could
    # silently produce an absolute path that then fails relative_to() later.
    candidates = [
        repo_path / (rel + ".py"),
        repo_path / rel / "__init__.py",
        repo_path / "src" / (rel + ".py"),
        repo_path / "src" / rel / "__init__.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                resolved = candidate.resolve()
                rel_result = resolved.relative_to(repo_path)
                rel_str = str(rel_result)
                if not rel_str.startswith("/"):
                    return rel_str
            except ValueError:
                pass
    return None


def _resolve_ts_import(
    source_file: str, import_path: str, repo_path: Path
) -> str | None:
    """
    Resolve a relative TypeScript/JS import path to a file path relative to repo root.
    Only resolves relative paths (starting with ./ or ../).
    repo_path must already be resolved by the caller.
    """
    if not import_path.startswith("./") and not import_path.startswith("../"):
        return None

    source_dir = (repo_path / source_file).parent
    target = (source_dir / import_path).resolve()

    # Guard: resolved target must be inside the repo root.
    try:
        target.relative_to(repo_path)
    except ValueError:
        return None

    # Try with common extensions
    extensions = ["", ".ts", ".tsx", ".js", ".jsx"]
    for ext in extensions:
        candidate = Path(str(target) + ext)
        if candidate.exists():
            try:
                rel_str = str(candidate.resolve().relative_to(repo_path))
                if not rel_str.startswith("/"):
                    return rel_str
            except ValueError:
                pass
        # Also try index file
        index = target / ("index" + ext) if ext else None
        if index and index.exists():
            try:
                rel_str = str(index.resolve().relative_to(repo_path))
                if not rel_str.startswith("/"):
                    return rel_str
            except ValueError:
                pass
    return None


def _detect_python_relationships(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Relationship]:
    repo_path = repo_path.resolve()
    results: list[Relationship] = []
    py_files = [e for e in file_entries if e.extension == ".py" and not _is_skipped(e.path)]

    for entry in py_files:
        try:
            content = (repo_path / entry.path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        modules_seen: set[str] = set()
        for m in _PY_IMPORT.finditer(content):
            modules_seen.add(m.group(1))
        for m in _PY_FROM.finditer(content):
            modules_seen.add(m.group(1))

        for module in modules_seen:
            resolved = _module_to_file(module, repo_path)
            if resolved and resolved != entry.path:
                results.append(
                    Relationship(
                        from_component=entry.path,
                        to_component=resolved,
                        type="imports",
                        confidence=0.6,
                        inferred=True,
                    )
                )
    return results


def _detect_ts_relationships(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Relationship]:
    repo_path = repo_path.resolve()
    ts_exts = {".ts", ".tsx", ".js", ".jsx"}
    results: list[Relationship] = []
    ts_files = [
        e for e in file_entries
        if e.extension in ts_exts and not _is_skipped(e.path)
    ]

    for entry in ts_files:
        try:
            content = (repo_path / entry.path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        imports_seen: set[str] = set()
        for m in _TS_IMPORT.finditer(content):
            imports_seen.add(m.group(1))

        for import_path in imports_seen:
            resolved = _resolve_ts_import(entry.path, import_path, repo_path)
            if resolved and resolved != entry.path:
                results.append(
                    Relationship(
                        from_component=entry.path,
                        to_component=resolved,
                        type="imports",
                        confidence=0.6,
                        inferred=True,
                    )
                )
    return results


def detect_relationships(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Relationship]:
    """
    Detect import relationships by scanning source files with regex.
    Only emits relationships where the target file exists in the repo.
    All results are inferred=True, confidence=0.6.
    """
    results: list[Relationship] = []
    results.extend(_detect_python_relationships(repo_path, file_entries))
    results.extend(_detect_ts_relationships(repo_path, file_entries))
    return results
