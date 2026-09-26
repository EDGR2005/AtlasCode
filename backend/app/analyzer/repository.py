from pathlib import Path

import git


def clone_repository(url: str, target_path: Path) -> str:
    """
    Shallow-clone (depth=1) a git repository to target_path.
    Returns the HEAD commit SHA.
    Raises git.GitCommandError on failure.
    Never executes any code from the repository.
    """
    target_path.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.clone_from(url, str(target_path), depth=1)
    return repo.head.commit.hexsha
