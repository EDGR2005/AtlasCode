from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from app.knowledge.storage import ProjectStorage

# Resolves to <workspace_root>/projects by default:
# backend/app/dependencies.py → parent = app → parent = backend → parent = workspace root
PROJECTS_DIR = Path(
    os.getenv(
        "PROJECTS_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "projects"),
    )
)


@lru_cache(maxsize=1)
def get_storage() -> ProjectStorage:
    return ProjectStorage(PROJECTS_DIR)
