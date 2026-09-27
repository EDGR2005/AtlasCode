"""
Contribution Orchestrator — Guided Mode

Two-phase mentor workflow:
  1. start_contribution() → BRANCHING → GUIDING  (sync, immediate)
  2. run_tests_for_user()  → TESTING → GUIDING|DONE  (on-demand, per user click)

Nothing pushes to a remote or creates a PR automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.knowledge.models import SessionMetrics, VerificationAttempt
from app.knowledge.storage import ProjectStorage
from app.contribution.repository_manager import create_branch, get_status
from app.contribution.test_runner import detect_test_command, run_tests


def start_contribution(
    project_id: str,
    issue_number: int,
    branch_name: str,
    storage: ProjectStorage,
) -> SessionMetrics:
    """
    Create branch and enter GUIDING state. Synchronous.
    """
    clone_path = storage.get_clone_path(project_id)
    knowledge = storage.load_knowledge(project_id)

    session = SessionMetrics(
        project_id=project_id,
        issue_number=issue_number,
        branch_name=branch_name,
        state="BRANCHING",
        started_at=datetime.now(timezone.utc),
    )
    storage.save_session(project_id, session)

    # --- BRANCHING ---
    try:
        create_branch(clone_path, branch_name)
    except ValueError:
        # Branch already exists — check it out instead
        import git
        repo = git.Repo(str(clone_path))
        repo.git.checkout(branch_name)
    except Exception as e:
        session.state = "FAILED"
        session.finished_at = datetime.now(timezone.utc)
        storage.save_session(project_id, session)
        raise e

    if knowledge:
        session.files_analyzed = len(knowledge.files)

    # Transition to GUIDING
    session.state = "GUIDING"
    session.changed_files = get_status(clone_path)
    storage.save_session(project_id, session)
    return session


def run_tests_for_user(
    project_id: str,
    storage: ProjectStorage,
) -> SessionMetrics:
    """
    Run test suite once. Called on-demand when user clicks 'Run Tests'.
    """
    session = storage.load_session(project_id)
    if not session:
        raise ValueError("No active session found")
        
    if session.state not in ("GUIDING", "DONE", "FAILED"):
        return session # don't run if currently busy

    clone_path = storage.get_clone_path(project_id)
    knowledge = storage.load_knowledge(project_id)
    
    session.state = "TESTING"
    session.changed_files = get_status(clone_path)
    session.files_modified = len(session.changed_files)
    storage.save_session(project_id, session)

    test_command = detect_test_command(knowledge, clone_path) if knowledge else None
    
    if test_command is None:
        # No test suite detected
        session.state = "DONE"
        session.finished_at = datetime.now(timezone.utc)
        storage.save_session(project_id, session)
        return session

    session.test_runs += 1
    
    # Run tests once
    result = run_tests(clone_path, test_command)
    
    session.tests_run += result.passed + result.failed + result.errors
    session.tests_passed += result.passed
    session.tests_failed += result.failed
    
    attempt = VerificationAttempt(attempt=session.test_runs, result=result)
    session.attempts.append(attempt)

    if result.timed_out or (result.failed == 0 and result.errors == 0):
        # Tests passed or timed out
        session.state = "DONE"
        session.finished_at = datetime.now(timezone.utc)
    else:
        # Tests failed, back to GUIDING
        session.state = "GUIDING"
        
    storage.save_session(project_id, session)
    return session
