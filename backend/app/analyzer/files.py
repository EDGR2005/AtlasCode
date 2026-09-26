import os
from pathlib import Path

from app.knowledge.models import FileEntry

IMPORTANT_FILENAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "pom.xml", "build.gradle", "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example",
}

IMPORTANT_PATTERNS = {".github/workflows"}  # path prefix patterns

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv",
    "dist", "build", "__pycache__", ".tox",
}


def scan_files(repo_path: Path) -> list[FileEntry]:
    """
    Walk the repository tree and return FileEntry for every non-skipped file.
    Mark is_important=True for manifest/config files.

    All stored paths are relative to repo_path (no leading slash).
    repo_path is resolved before walking so that os.walk's dirpath strings
    always match the resolved base and relative_to() never raises ValueError.
    """
    # Resolve once so symlinks and ".." segments are normalised.
    root = repo_path.resolve()

    entries: list[FileEntry] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            abs_path = Path(dirpath) / filename
            # Guard: skip any path that resolves outside the repository root.
            resolved_abs = abs_path.resolve()
            try:
                rel_path = resolved_abs.relative_to(root)
            except ValueError:
                # File is outside the repo root (e.g. a broken symlink target).
                continue
            rel_str = str(rel_path)
            # Sanity check: relative paths must never be absolute.
            if rel_str.startswith("/"):
                continue
            size = abs_path.stat().st_size
            ext = abs_path.suffix
            important = (
                filename in IMPORTANT_FILENAMES
                or any(rel_str.startswith(p) for p in IMPORTANT_PATTERNS)
            )
            entries.append(FileEntry(
                path=rel_str,
                size_bytes=size,
                extension=ext,
                is_important=important,
            ))
    return entries
