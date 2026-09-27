"""
Repository Manager — Sprint 1

Provides Git branch, diff, status, and commit operations over an already-cloned
repository. All functions are pure wrappers around GitPython and operate only on
the local working tree. Nothing in this module pushes to a remote or executes
any code from the repository.

Branch naming convention: atlas/{issue_number}-{slug}
Example: atlas/123-fix-expired-token
"""
from __future__ import annotations

import re
from pathlib import Path

import git
from git.exc import GitCommandError


# ---------------------------------------------------------------------------
# Branch name helpers
# ---------------------------------------------------------------------------

def make_branch_name(issue_number: int, title: str) -> str:
    """
    Produce a safe branch name from an issue number and title.
    Example: make_branch_name(42, "Fix expired token validation")
             → "atlas/42-fix-expired-token-validation"
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip()).strip("-").lower()
    # Cap slug length to keep branch names manageable
    slug = slug[:50].rstrip("-")
    return f"atlas/{issue_number}-{slug}"


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def get_repo(clone_path: Path) -> git.Repo:
    """Return a GitPython Repo for the given clone path."""
    return git.Repo(str(clone_path))


def create_branch(clone_path: Path, branch_name: str) -> None:
    """
    Create a new branch from the current HEAD and check it out.
    Raises ValueError if the branch already exists.
    """
    repo = get_repo(clone_path)
    if branch_name in [h.name for h in repo.heads]:
        raise ValueError(f"Branch '{branch_name}' already exists.")
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()


def get_current_branch(clone_path: Path) -> str:
    """
    Return the name of the currently checked-out branch.
    Returns "(detached HEAD)" when the repo is in detached HEAD state
    (e.g. after a shallow clone before any branch operations).
    """
    repo = get_repo(clone_path)
    try:
        return repo.active_branch.name
    except TypeError:
        return "(detached HEAD)"


def get_status(clone_path: Path) -> list[str]:
    """
    Return a list of relative file paths that are modified, added, or deleted
    in the working tree compared to the index/HEAD.
    Untracked files are included.
    """
    repo = get_repo(clone_path)
    changed: list[str] = []

    # Modified / deleted tracked files
    for item in repo.index.diff(None):
        changed.append(item.a_path)

    # Staged changes (index vs HEAD)
    if repo.head.is_valid():
        for item in repo.index.diff("HEAD"):
            if item.a_path not in changed:
                changed.append(item.a_path)

    # Untracked files
    for path in repo.untracked_files:
        if path not in changed:
            changed.append(path)

    return changed


def get_diff(clone_path: Path) -> str:
    """
    Return a unified diff string of all working-tree changes vs HEAD.
    Returns an empty string when there are no changes.
    """
    repo = get_repo(clone_path)
    if not repo.head.is_valid():
        return ""
    # diff between HEAD and the working tree
    return repo.git.diff("HEAD")


def commit_all(clone_path: Path, message: str) -> str:
    """
    Stage all currently tracked modified/deleted files and commit with the
    given message. Returns the new commit SHA.

    Does NOT add untracked files (use git add explicitly for those).
    Does NOT push to any remote.
    Raises ValueError if there is nothing to commit.
    """
    repo = get_repo(clone_path)

    # Stage all tracked changes
    repo.git.add("-u")

    # Verify there is something staged
    if not repo.index.diff("HEAD") and not repo.is_dirty(index=True):
        raise ValueError("Nothing to commit — working tree is clean.")

    commit = repo.index.commit(message)
    return commit.hexsha

def commit_selected(clone_path: Path, message: str, files: list[str]) -> str:
    """
    Stage the specified files (or all changes if empty) and commit.
    """
    repo = get_repo(clone_path)

    if not files:
        repo.git.add(".")
    else:
        for f in files:
            try:
                repo.git.add(f)
            except GitCommandError:
                pass # might be deleted

    if not repo.index.diff("HEAD") and not repo.is_dirty(index=True):
        raise ValueError("Nothing to commit — working tree is clean.")

    commit = repo.index.commit(message)
    return commit.hexsha
