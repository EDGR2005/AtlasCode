"""
Issue → Code Mapper — Sprint 3

Maps issue text to relevant files in a cloned repository using keyword
search. All results are heuristic (inferred=True).
"""
from __future__ import annotations

import re
from pathlib import Path

from app.knowledge.models import FileEntry, ProjectKnowledge, RelevantFile

# Stop words to strip before keyword matching
_STOP_WORDS = {
    "the", "a", "an", "is", "it", "in", "on", "at", "to", "for", "of",
    "and", "or", "but", "not", "with", "this", "that", "are", "was",
    "be", "as", "by", "from", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "i",
    "we", "you", "he", "she", "they", "them", "their", "our", "my",
    "when", "where", "which", "what", "who", "how", "if", "then",
    "its", "into", "about", "also", "more", "than", "so", "up", "out",
    "there", "here", "after", "before", "just", "all", "any", "some",
}

_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv",
    "dist", "build", "__pycache__", ".tox",
}

_MAX_FILES_SCANNED = 300
_MAX_RESULTS = 10


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from issue title + body."""
    # Lowercase, split on non-alphanumeric
    tokens = re.findall(r"[a-z][a-z0-9_]{2,}", text.lower())
    seen: dict[str, int] = {}
    for tok in tokens:
        if tok not in _STOP_WORDS:
            seen[tok] = seen.get(tok, 0) + 1
    # Return tokens that appear at least once, sorted by frequency desc
    return [k for k, _ in sorted(seen.items(), key=lambda x: -x[1])]


def _is_skipped(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    return any(p in _SKIP_DIRS for p in parts)


def _score_file(
    entry: FileEntry,
    keywords: list[str],
    repo_path: Path,
) -> tuple[int, list[str]]:
    """
    Score a file by how many keywords appear in its path and content.
    Returns (score, matched_keywords).
    """
    path_lower = entry.path.replace("\\", "/").lower()
    matched: set[str] = set()

    # Path-level matches (weighted higher — 2 pts each)
    score = 0
    for kw in keywords:
        if kw in path_lower:
            matched.add(kw)
            score += 2

    # Content-level matches (1 pt each, bounded read)
    try:
        content = (repo_path / entry.path).read_text(encoding="utf-8", errors="ignore")
        content_lower = content.lower()
        for kw in keywords:
            if kw in content_lower:
                matched.add(kw)
                score += 1
    except OSError:
        pass

    return score, list(matched)


def map_issue_to_files(
    issue: dict,
    knowledge: ProjectKnowledge,
    clone_path: Path,
) -> list[RelevantFile]:
    """
    Return up to _MAX_RESULTS RelevantFile objects, ranked by relevance score.
    Each entry carries a human-readable reason string.
    """
    title = issue.get("title", "")
    body = issue.get("body") or ""
    combined = f"{title} {body}"
    keywords = _extract_keywords(combined)[:20]  # use top 20 keywords

    if not keywords:
        return []

    repo_path = clone_path.resolve()
    scored: list[tuple[int, list[str], FileEntry]] = []
    scanned = 0

    for entry in knowledge.files:
        if _is_skipped(entry.path):
            continue
        if scanned >= _MAX_FILES_SCANNED:
            break
        scanned += 1

        score, matched = _score_file(entry, keywords, repo_path)
        if score > 0:
            scored.append((score, matched, entry))

    # Sort by score descending
    scored.sort(key=lambda x: -x[0])

    results: list[RelevantFile] = []
    for score, matched, entry in scored[:_MAX_RESULTS]:
        kw_str = ", ".join(f'"{k}"' for k in matched[:4])
        reason = f"Matched keyword(s) {kw_str} in {'path and content' if any(k in entry.path.lower() for k in matched) else 'content'}."
        results.append(RelevantFile(path=entry.path, reason=reason, inferred=True))

    return results
