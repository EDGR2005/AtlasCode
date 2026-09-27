"""
Test Runner — Sprint 4

Detects and runs the project's test suite via subprocess.
Hard limits: 120 second timeout. Never installs packages.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from app.knowledge.models import ProjectKnowledge, TestResult

_TIMEOUT_SECONDS = 120
_MAX_OUTPUT_CHARS = 4000

# Commands that must never be run
_BLOCKED_COMMANDS = {
    "pip install", "pip3 install", "npm install", "yarn install",
    "pnpm install", "cargo build", "make install", "apt", "brew",
}


def detect_test_command(knowledge: ProjectKnowledge, clone_path: Path) -> str | None:
    """
    Detect the appropriate test command for this repository.
    Returns None when no supported test framework is found.
    """
    tech_names = {t.name.lower() for t in knowledge.technologies}
    dep_names = {d.name.lower() for d in knowledge.dependencies}

    # Python
    if "python" in tech_names:
        if "pytest" in dep_names:
            return "python -m pytest -v"
        # Check for pytest in requirements.txt / pyproject.toml on disk
        for fname in ("requirements.txt", "pyproject.toml"):
            fpath = clone_path / fname
            if fpath.exists():
                content = fpath.read_text(errors="ignore").lower()
                if "pytest" in content:
                    return "python -m pytest -v"
        return "python -m unittest discover"

    # Node / TypeScript / JavaScript
    if any(t in tech_names for t in ("node.js", "javascript", "typescript")):
        pkg = clone_path / "package.json"
        if pkg.exists():
            import json
            try:
                data = json.loads(pkg.read_text())
                scripts = data.get("scripts", {})
                if "test" in scripts:
                    return "npm test"
            except Exception:
                pass

    # Rust
    if "rust" in tech_names:
        return "cargo test"

    # Go
    if "go" in tech_names:
        return "go test ./..."

    return None


def run_tests(clone_path: Path, command: str) -> TestResult:
    """
    Run the given test command inside clone_path.
    Returns a TestResult with pass/fail counts and truncated output.
    Never installs packages or executes destructive commands.
    """
    # Safety check — blocked commands must not be run
    for blocked in _BLOCKED_COMMANDS:
        if blocked in command.lower():
            return TestResult(
                output=f"Blocked command: {command!r} — install commands are not allowed.",
                timed_out=False,
            )

    start = time.monotonic()
    timed_out = False
    raw_output = ""

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(clone_path),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
        raw_output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired as e:
        timed_out = True
        raw_output = (e.stdout or "") + (e.stderr or "") if hasattr(e, "stdout") else ""
        raw_output += f"\n[TIMEOUT after {_TIMEOUT_SECONDS}s]"
    except Exception as e:
        raw_output = f"[ERROR running tests: {e}]"

    duration = time.monotonic() - start
    output = raw_output[:_MAX_OUTPUT_CHARS]

    passed, failed, errors = _parse_results(raw_output, command)

    return TestResult(
        passed=passed,
        failed=failed,
        errors=errors,
        output=output,
        duration_seconds=round(duration, 2),
        timed_out=timed_out,
    )


def _parse_results(output: str, command: str) -> tuple[int, int, int]:
    """Extract pass/fail/error counts from test output."""
    passed = failed = errors = 0

    if "pytest" in command:
        # pytest: "5 passed, 1 failed, 0 errors"
        m = re.search(r"(\d+) passed", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+) error", output)
        if m:
            errors = int(m.group(1))

    elif "npm test" in command:
        # Jest / Mocha: "Tests: 3 passed, 1 failed"
        m = re.search(r"(\d+) passed", output, re.IGNORECASE)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", output, re.IGNORECASE)
        if m:
            failed = int(m.group(1))

    elif "cargo test" in command:
        # "test result: ok. 5 passed; 0 failed"
        m = re.search(r"(\d+) passed", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", output)
        if m:
            failed = int(m.group(1))

    elif "go test" in command:
        passed_count = output.count("--- PASS")
        failed_count = output.count("--- FAIL")
        passed = passed_count
        failed = failed_count

    return passed, failed, errors
