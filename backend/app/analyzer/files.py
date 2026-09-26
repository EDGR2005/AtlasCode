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
    """
    entries: list[FileEntry] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            abs_path = Path(dirpath) / filename
            rel_path = abs_path.relative_to(repo_path)
            rel_str = str(rel_path)
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
