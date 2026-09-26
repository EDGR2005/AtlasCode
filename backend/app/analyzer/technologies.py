from __future__ import annotations

import json
import re
from pathlib import Path

from app.knowledge.models import FileEntry, TechnologyDetection


def _ver(constraint: str) -> str | None:
    """Extract a version number from a constraint string like '>=0.111.0' or '^4.19.2'."""
    m = re.search(r"[\d]+(?:\.[\d]+)*", constraint)
    return m.group(0) if m else None


def _merge(
    detected: dict[str, TechnologyDetection],
    name: str,
    version: str | None,
    source: str,
    confidence: float,
) -> None:
    """Add or replace a TechnologyDetection, keeping the higher-confidence entry."""
    existing = detected.get(name)
    if existing is None:
        detected[name] = TechnologyDetection(
            name=name, version=version, source=source, confidence=confidence
        )
    else:
        # Replace if higher confidence, or if same confidence but new one has a version
        if confidence > existing.confidence or (
            confidence == existing.confidence
            and version is not None
            and existing.version is None
        ):
            detected[name] = TechnologyDetection(
                name=name, version=version, source=source, confidence=confidence
            )


def _parse_package_json(
    repo_path: Path, detected: dict[str, TechnologyDetection]
) -> None:
    pkg_path = repo_path / "package.json"
    if not pkg_path.exists():
        return

    try:
        data = json.loads(pkg_path.read_text())
    except Exception:
        return

    deps: dict[str, str] = {}
    deps.update(data.get("dependencies") or {})
    dev_deps: dict[str, str] = {}
    dev_deps.update(data.get("devDependencies") or {})
    all_deps = {**deps, **dev_deps}

    _merge(detected, "Node.js", None, "package.json", 0.9)
    _merge(detected, "JavaScript", None, "package.json", 0.8)

    if "react" in all_deps or "@types/react" in all_deps:
        version = _ver(deps.get("react", ""))
        _merge(detected, "React", version, "package.json", 1.0)

    if "typescript" in all_deps or "@types/node" in all_deps:
        version = _ver(dev_deps.get("typescript", "") or deps.get("typescript", ""))
        _merge(detected, "TypeScript", version, "package.json", 1.0)

    if "next" in all_deps:
        version = _ver(deps.get("next", ""))
        _merge(detected, "Next.js", version, "package.json", 1.0)

    if "express" in all_deps:
        version = _ver(deps.get("express", ""))
        _merge(detected, "Express", version, "package.json", 1.0)


def _parse_pyproject_toml(
    repo_path: Path, detected: dict[str, TechnologyDetection]
) -> None:
    pp_path = repo_path / "pyproject.toml"
    if not pp_path.exists():
        return

    try:
        # Use tomllib (stdlib ≥ 3.11) or fall back to tomli
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(pp_path.read_text())
    except Exception:
        return

    _merge(detected, "Python", None, "pyproject.toml", 1.0)

    dep_lines: list[str] = (
        (data.get("project") or {}).get("dependencies") or []
    )
    _detect_python_framework_deps(dep_lines, "pyproject.toml", detected)


def _detect_python_framework_deps(
    dep_lines: list[str], source: str, detected: dict[str, TechnologyDetection]
) -> None:
    for line in dep_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if lower.startswith("fastapi"):
            version = _ver(line[len("fastapi"):])
            _merge(detected, "FastAPI", version, source, 1.0)
        elif lower.startswith("django"):
            version = _ver(line[len("django"):])
            _merge(detected, "Django", version, source, 1.0)
        elif lower.startswith("flask"):
            version = _ver(line[len("flask"):])
            _merge(detected, "Flask", version, source, 1.0)


def _parse_requirements_txt(
    repo_path: Path, detected: dict[str, TechnologyDetection]
) -> None:
    req_path = repo_path / "requirements.txt"
    if not req_path.exists():
        return

    _merge(detected, "Python", None, "requirements.txt", 0.9)

    lines = req_path.read_text().splitlines()
    _detect_python_framework_deps(lines, "requirements.txt", detected)


def _parse_go_mod(
    repo_path: Path, detected: dict[str, TechnologyDetection]
) -> None:
    go_mod = repo_path / "go.mod"
    if not go_mod.exists():
        return

    for line in go_mod.read_text().splitlines():
        m = re.match(r"^go\s+([\d.]+)", line.strip())
        if m:
            _merge(detected, "Go", m.group(1), "go.mod", 1.0)
            return

    # go.mod exists but no version directive found
    _merge(detected, "Go", None, "go.mod", 1.0)


def _parse_cargo_toml(
    repo_path: Path, detected: dict[str, TechnologyDetection]
) -> None:
    cargo = repo_path / "Cargo.toml"
    if not cargo.exists():
        return
    _merge(detected, "Rust", None, "Cargo.toml", 1.0)


def _parse_dockerfile(
    repo_path: Path, detected: dict[str, TechnologyDetection]
) -> None:
    dockerfile = repo_path / "Dockerfile"
    if not dockerfile.exists():
        return

    _merge(detected, "Docker", None, "Dockerfile", 1.0)
    for line in dockerfile.read_text().splitlines():
        line = line.strip()
        if line.upper().startswith("FROM"):
            image = line.split()[1] if len(line.split()) > 1 else ""
            if image.startswith("python:"):
                _merge(detected, "Python", None, "Dockerfile", 0.9)
            elif image.startswith("node:"):
                _merge(detected, "Node.js", None, "Dockerfile", 0.9)


def _parse_github_actions(
    repo_path: Path, file_entries: list[FileEntry], detected: dict[str, TechnologyDetection]
) -> None:
    for entry in file_entries:
        if entry.path.startswith(".github/workflows"):
            _merge(detected, "GitHub Actions", None, entry.path, 1.0)
            return


def _detect_from_extensions(
    file_entries: list[FileEntry], detected: dict[str, TechnologyDetection]
) -> None:
    ext_map = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
    }
    for entry in file_entries:
        tech = ext_map.get(entry.extension)
        if tech and tech not in detected:
            _merge(detected, tech, None, "file_extension", 0.7)


def detect_technologies(
    repo_path: Path, file_entries: list[FileEntry]
) -> list[TechnologyDetection]:
    """Detect technologies from manifest files and file extensions."""
    detected: dict[str, TechnologyDetection] = {}

    _parse_package_json(repo_path, detected)
    _parse_pyproject_toml(repo_path, detected)
    _parse_requirements_txt(repo_path, detected)
    _parse_go_mod(repo_path, detected)
    _parse_cargo_toml(repo_path, detected)
    _parse_dockerfile(repo_path, detected)
    _parse_github_actions(repo_path, file_entries, detected)

    # TypeScript from .ts files if not already detected via package.json
    if "TypeScript" not in detected:
        for entry in file_entries:
            if entry.extension in (".ts", ".tsx"):
                _merge(detected, "TypeScript", None, "file_extension", 0.7)
                break

    # Extension-based fallbacks
    _detect_from_extensions(file_entries, detected)

    return list(detected.values())
