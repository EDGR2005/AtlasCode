from __future__ import annotations

import json
import re
from pathlib import Path

from app.knowledge.models import Dependency, FileEntry


def _parse_pep508_line(line: str) -> tuple[str, str | None]:
    """
    Parse a PEP 508 dependency string like 'fastapi>=0.111.0' or 'pydantic==2.7.0'.
    Returns (name, version_spec) where version_spec may be None.
    """
    line = line.strip()
    # Strip extras like 'package[extra]>=1.0'
    m = re.match(r"^([A-Za-z0-9_\-\.]+)(?:\[.*?\])?\s*([><=!~^].+)?$", line)
    if not m:
        return line, None
    name = m.group(1).lower().replace("_", "-")
    spec = m.group(2).strip() if m.group(2) else None
    return name, spec


def _extract_package_json(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Dependency]:
    pkg_path = repo_path / "package.json"
    if not pkg_path.exists():
        return []

    try:
        data = json.loads(pkg_path.read_text())
    except Exception:
        return []

    results: list[Dependency] = []
    for section in ("dependencies", "devDependencies"):
        for name, version_spec in (data.get(section) or {}).items():
            results.append(
                Dependency(
                    name=name,
                    version=version_spec or None,
                    ecosystem="npm",
                    source="package.json",
                )
            )
    return results


def _extract_requirements_txt(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Dependency]:
    req_path = repo_path / "requirements.txt"
    if not req_path.exists():
        return []

    results: list[Dependency] = []
    for line in req_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, spec = _parse_pep508_line(line)
        results.append(
            Dependency(name=name, version=spec, ecosystem="pypi", source="requirements.txt")
        )
    return results


def _extract_pyproject_toml(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Dependency]:
    pp_path = repo_path / "pyproject.toml"
    if not pp_path.exists():
        return []

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(pp_path.read_text())
    except Exception:
        return []

    dep_lines: list[str] = (data.get("project") or {}).get("dependencies") or []
    results: list[Dependency] = []
    for line in dep_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, spec = _parse_pep508_line(line)
        results.append(
            Dependency(name=name, version=spec, ecosystem="pypi", source="pyproject.toml")
        )
    return results


def _extract_go_mod(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Dependency]:
    go_mod = repo_path / "go.mod"
    if not go_mod.exists():
        return []

    results: list[Dependency] = []
    in_require_block = False
    for line in go_mod.read_text().splitlines():
        stripped = line.strip()
        if stripped == "require (":
            in_require_block = True
            continue
        if in_require_block and stripped == ")":
            in_require_block = False
            continue
        if in_require_block or stripped.startswith("require "):
            # Handle single-line: require module/path v1.2.3
            if stripped.startswith("require "):
                stripped = stripped[len("require "):].strip()
            parts = stripped.split()
            if len(parts) >= 2:
                results.append(
                    Dependency(
                        name=parts[0],
                        version=parts[1],
                        ecosystem="go",
                        source="go.mod",
                    )
                )
    return results


def _extract_cargo_toml(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Dependency]:
    cargo = repo_path / "Cargo.toml"
    if not cargo.exists():
        return []

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(cargo.read_text())
    except Exception:
        return []

    results: list[Dependency] = []
    for name, spec in (data.get("dependencies") or {}).items():
        version = spec if isinstance(spec, str) else (spec.get("version") if isinstance(spec, dict) else None)
        results.append(
            Dependency(name=name, version=version, ecosystem="cargo", source="Cargo.toml")
        )
    return results


def extract_dependencies(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[Dependency]:
    """Extract direct dependencies from manifest files."""
    results: list[Dependency] = []
    results.extend(_extract_package_json(repo_path, file_entries))
    results.extend(_extract_requirements_txt(repo_path, file_entries))
    results.extend(_extract_pyproject_toml(repo_path, file_entries))
    results.extend(_extract_go_mod(repo_path, file_entries))
    results.extend(_extract_cargo_toml(repo_path, file_entries))
    return results
