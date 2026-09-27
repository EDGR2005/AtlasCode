# AtlasCode — Contribution Agent Plan

> **Vision:** "Your first contribution to Open Source, guided from issue to pull request."

---

## Current Architecture Audit

### What exists today

| Layer | Component | Status |
|---|---|---|
| Backend | FastAPI app (`app/main.py`) | ✅ Running |
| Backend | 7 REST endpoints (`app/api/projects.py`) | ✅ Complete |
| Backend | Analysis pipeline — clone, scan, tech, deps, relationships, database (`app/analyzer/`) | ✅ Complete |
| Backend | Filesystem JSON storage (`app/knowledge/storage.py`) | ✅ Complete |
| Backend | Pydantic knowledge model (`app/knowledge/models.py`) | ✅ Complete |
| Backend | MCP stdio server — 6 tools (`app/mcp/server.py`) | ✅ Complete |
| Backend | GitPython shallow clone (`app/analyzer/repository.py`) | ✅ depth=1 |
| Frontend | React dashboard — 6 tabs (`pages/DashboardPage.tsx`) | ✅ Complete |
| Frontend | DB diagram panel (`components/DatabasePanel.tsx`) | ✅ Fixed |
| Infra | Docker Compose — backend:8000, frontend:3000 | ✅ Working |
| Infra | Volume mount `./projects:/app/projects` | ✅ Correct |

### What is missing for the Contribution Agent

| Needed capability | Current state |
|---|---|
| GitHub Issues API (fetch, label, classify) | ❌ Not present |
| Issue → code mapping (keyword → file search) | ❌ Not present |
| Git branch creation / checkout | ❌ Not present (only clone exists) |
| Git diff / commit / push | ❌ Not present |
| Test runner (execute tests inside container) | ❌ Not present |
| Pull Request draft generator | ❌ Not present |
| Contribution workflow orchestrator | ❌ Not present |
| Session metrics recorder | ❌ Not present |
| Frontend: contribution workflow UI | ❌ Not present |

### Files that will be modified

- `backend/app/analyzer/repository.py` — extend with branch/diff/commit helpers
- `backend/app/knowledge/models.py` — add `IssueAnalysis`, `ContributionPlan`, `SessionMetrics` models
- `backend/app/main.py` — register new routers
- `backend/requirements.txt` — add `httpx` (already present), no new deps needed
- `docker-compose.yml` — add `GITHUB_TOKEN` env var (optional, for rate limits)
- `frontend/src/api/client.ts` — add contribution workflow API calls
- `frontend/src/types/knowledge.ts` — add issue/contribution types
- `frontend/src/pages/DashboardPage.tsx` — add Contribute tab
- `frontend/src/App.tsx` — no change needed

### Files that will be created

```
backend/app/
  github/
    __init__.py
    client.py          # GitHub REST API wrapper (issues, labels, comments)
    issue_analyzer.py  # suitability analysis — no scoring, only reasons
  contribution/
    __init__.py
    repository_manager.py  # branch, diff, commit, push (wraps GitPython)
    issue_mapper.py        # issue keywords → relevant files
    plan_generator.py      # produces ContributionPlan struct
    test_runner.py         # runs test suite, captures output, parses results
    pr_generator.py        # generates commit message + PR draft markdown
    session.py             # records SessionMetrics
    orchestrator.py        # state machine: UNDERSTAND → PLAN → IMPLEMENT → VERIFY → SUMMARISE
  api/
    contribution.py        # new FastAPI router: /projects/{id}/contribute/*

frontend/src/
  pages/ContributePage.tsx
  components/
    IssueList.tsx
    IssueSuitability.tsx
    ContributionPlan.tsx
    VerificationLoop.tsx
    DiffViewer.tsx
    ContributionSummary.tsx

backend/tests/
  test_github_client.py
  test_repository_manager.py
  test_issue_mapper.py
  test_plan_generator.py
  test_session.py
```

---

## Implementation Order

Implement strictly sprint by sprint. Do not start a later sprint until all tests in the current sprint pass.

---

## Sprint 1 — Repository Manager

**Intent:** Extend the existing GitPython integration so the system can manage branches, read diffs, and make commits — the minimal Git operations needed before any code change can be safely made.

**Expected Outcomes:**
- `repository_manager.py` exists and passes all tests
- Can create a branch named `atlas/<issue>-<slug>`
- Can read `git diff` as a string
- Can stage all tracked changes and commit with a message
- Can report current branch name and dirty-file list
- `clone_repository` already works (do not break existing tests)

**Todo List:**
1. Create `backend/app/contribution/__init__.py`
2. Create `backend/app/contribution/repository_manager.py` with:
   - `get_repo(clone_path)` — returns `git.Repo`
   - `create_branch(clone_path, branch_name)` — creates and checks out branch
   - `get_current_branch(clone_path)` — returns branch name string
   - `get_status(clone_path)` — returns list of modified/untracked file paths
   - `get_diff(clone_path)` — returns unified diff string
   - `commit_all(clone_path, message)` — stages modified tracked files and commits
3. Create `backend/tests/test_repository_manager.py` — all offline using `tmp_path` + `git.Repo.init()`
4. Run `pytest backend/tests/test_repository_manager.py` — all must pass

**Relevant Context:**
- `backend/app/analyzer/repository.py` — existing `clone_repository()` uses `git.Repo.clone_from(..., depth=1)`. Do not modify it.
- `backend/requirements.txt` — `gitpython>=3.1.43` already present
- Branch name format: `atlas/{issue_number}-{slug}` e.g. `atlas/123-fix-validation`

**Status:** `[x] done`

---

## Sprint 2 — GitHub Issue Analyzer

**Intent:** Fetch open issues from a GitHub repository and produce a structured suitability analysis for each one. No scoring system — only human-readable reasons.

**Expected Outcomes:**
- `github/client.py` can fetch open issues via the GitHub REST API (unauthenticated, or token via env var)
- `github/issue_analyzer.py` classifies issues by type, estimated scope, and produces a list of checkable reasons why the issue is or is not approachable
- Works offline in tests using fixture JSON responses (no real network calls in CI)

**Todo List:**
1. Create `backend/app/github/__init__.py`
2. Create `backend/app/github/client.py`:
   - `get_open_issues(owner, repo, token=None)` — GET `https://api.github.com/repos/{owner}/{repo}/issues?state=open`
   - Returns `list[dict]` (raw GitHub issue objects)
   - Respects `GITHUB_TOKEN` env var if present
   - Uses `httpx` (already in requirements)
3. Create `backend/app/github/issue_analyzer.py`:
   - `analyze_issue(issue: dict) -> IssueAnalysis` — produce structured analysis
   - Detect beginner signals: labels (`good first issue`, `help wanted`, `bug`, `documentation`, `easy`, `beginner`, `small`), title keywords, body length, existing comments
   - Produce `reasons: list[str]` (positive signals) and `concerns: list[str]` (risk signals)
   - Estimate `scope`: `"small" | "medium" | "large" | "unknown"` from body length + label hints
   - Estimate `type`: `"bug" | "docs" | "feature" | "refactor" | "unknown"`
   - No numerical score
4. Add `IssueAnalysis` Pydantic model to `backend/app/knowledge/models.py`
5. Create `backend/tests/test_github_client.py` — mock `httpx` responses, no network
6. Create `backend/tests/test_issue_analyzer.py` — unit test reason detection logic
7. Run all new tests — all must pass

**Relevant Context:**
- `httpx` already in `requirements.txt`
- GitHub unauthenticated rate limit: 60 req/hour. Token raises it to 5000. Add `GITHUB_TOKEN` to `docker-compose.yml` as an optional env var.
- Do NOT parse issue body as markdown — treat as plain text for keyword matching

**Status:** `[x] done`

---

## Sprint 3 — Issue → Code Mapper + Contribution Plan

**Intent:** Given an issue's text, find the files in the already-cloned repository that are most likely relevant. Then produce a step-by-step contribution plan the user must approve before any code is written.

**Expected Outcomes:**
- `issue_mapper.py` returns a ranked list of `RelevantFile` objects with a reason string per file
- `plan_generator.py` produces a `ContributionPlan` with ordered steps
- A new REST endpoint `POST /projects/{id}/contribute/plan` accepts an issue number and returns a `ContributionPlan`
- Frontend: plan is displayed with an `[Approve Plan]` button; no code is written until the user clicks it

**Todo List:**
1. Create `backend/app/contribution/issue_mapper.py`:
   - `map_issue_to_files(issue: dict, knowledge: ProjectKnowledge, clone_path: Path) -> list[RelevantFile]`
   - Extract keywords from issue title and body (strip stop words, deduplicate)
   - Search file paths and file contents (reuse `_search_code` logic from MCP server)
   - Return up to 10 files, each with a `reason` string explaining why it's relevant
2. Create `backend/app/contribution/plan_generator.py`:
   - `generate_plan(issue, relevant_files, knowledge) -> ContributionPlan`
   - Steps always include: understand, locate tests, create branch, write reproduction test, implement, run tests, review diff
   - Steps are plain-language sentences, not code
3. Add `RelevantFile`, `ContributionPlan`, `ContributionStep` Pydantic models to `models.py`
4. Create `backend/app/api/contribution.py` router with:
   - `POST /projects/{id}/contribute/issues` — fetch and analyze GitHub issues for a project
   - `POST /projects/{id}/contribute/plan` — body: `{issue_number: int}`, returns `ContributionPlan`
5. Register new router in `backend/app/main.py`
6. Create `backend/tests/test_issue_mapper.py` — offline using existing fixture repos
7. Create `backend/tests/test_plan_generator.py`
8. Run all tests

**Relevant Context:**
- `knowledge.repository.url` contains the GitHub URL, parse owner/repo from it
- `storage.get_clone_path(project_id)` returns path to cloned repo
- Reuse `_search_code` from `app/mcp/server.py` — extract it into a shared utility to avoid duplication
- File relevance is heuristic — clearly mark `inferred=True` in all `RelevantFile` objects

**Status:** `[x] done`

---

## Sprint 4 — Coding Agent (Test → Implement → Verify Loop)

**Intent:** Once the user approves the plan, execute the contribution: create the branch, attempt implementation, run the test suite, and loop up to `MAX_FIX_ATTEMPTS = 3` times on failure.

**Expected Outcomes:**
- `test_runner.py` can discover and run the project's test suite (pytest, npm test, etc.) inside the container and return structured results
- `orchestrator.py` implements the state machine: `BRANCH → IMPLEMENT → TEST → (FIX → TEST)*` with a hard cap of 3 fix attempts
- Each attempt result is stored as `VerificationAttempt` with pass/fail counts and failure output
- `SessionMetrics` is updated after each step
- A new endpoint `POST /projects/{id}/contribute/execute` starts the loop (async background task)
- A new endpoint `GET /projects/{id}/contribute/status` returns current orchestrator state + attempts so far

**Todo List:**
1. Create `backend/app/contribution/test_runner.py`:
   - `detect_test_command(knowledge, clone_path) -> str | None` — detect `pytest`, `npm test`, `cargo test`, etc. from knowledge model
   - `run_tests(clone_path, command) -> TestResult` — run via `subprocess`, capture stdout/stderr, parse pass/fail counts
   - Hard timeout: 120 seconds
   - Never install packages (`pip install`, `npm install`) — only run test commands
2. Create `backend/app/contribution/session.py`:
   - `SessionMetrics` model fields: `issue_number`, `files_analyzed`, `files_modified`, `tests_run`, `tests_passed`, `tests_failed`, `fix_attempts`, `status`
   - Persisted as `session.json` in the project directory alongside `knowledge.json`
3. Create `backend/app/contribution/orchestrator.py`:
   - State machine with states: `IDLE | BRANCHING | IMPLEMENTING | TESTING | FIXING | DONE | FAILED`
   - `MAX_FIX_ATTEMPTS = 3`
   - On each state transition, write `session.json`
   - Never push, never create PR automatically — those require explicit user action
4. Add `TestResult`, `VerificationAttempt`, `SessionMetrics` models to `models.py`
5. Add `POST /projects/{id}/contribute/execute` and `GET /projects/{id}/contribute/status` to `contribution.py` router
6. Create `backend/tests/test_test_runner.py` — mock `subprocess`, offline
7. Create `backend/tests/test_orchestrator.py` — unit test state transitions
8. Run all tests

**Relevant Context:**
- `subprocess.run(..., cwd=clone_path, timeout=120, capture_output=True)` is the safe execution pattern
- The container already has Python/pytest available; Node/npm only if the analyzed repo uses Node
- Do NOT call `git push` in this sprint — push is in Sprint 5 with user approval gate
- Implementation in this sprint is a stub (`pass`) — the actual LLM-driven code modification is out of scope for Phase 1. The orchestrator flow and verification loop must work end-to-end with a no-op implementation step.

**Status:** `[x] done`

---

## Sprint 5 — Contribution Output (Commit + PR Generator)

**Intent:** After a successful verification loop, produce the commit, show the diff, generate the PR description, and expose explicit user-gated actions for pushing and creating the draft PR.

**Expected Outcomes:**
- `pr_generator.py` produces a conventional-commit message suggestion and a PR markdown draft
- `GET /projects/{id}/contribute/diff` returns the current unified diff
- `POST /projects/{id}/contribute/commit` stages and commits (requires user call — not automatic)
- `POST /projects/{id}/contribute/pr-draft` returns the PR markdown (does NOT push or open GitHub PR)
- `ContributionSummary` struct is returned when the session reaches `DONE`

**Todo List:**
1. Create `backend/app/contribution/pr_generator.py`:
   - `generate_commit_message(issue, relevant_files, summary) -> str` — conventional commit format: `type(scope): description`
   - `generate_pr_draft(issue, plan, metrics, commit_message) -> str` — markdown string with Summary / Changes / Testing / Related Issue sections
2. Add `ContributionSummary` model to `models.py`
3. Add endpoints to `contribution.py` router:
   - `GET /projects/{id}/contribute/diff` — returns `{"diff": "...unified diff string..."}` 
   - `POST /projects/{id}/contribute/commit` — body: `{message: str}`, commits and returns new SHA
   - `GET /projects/{id}/contribute/summary` — returns `ContributionSummary`
   - `GET /projects/{id}/contribute/pr-draft` — returns `{"markdown": "..."}` (no GitHub API call)
4. Add frontend components:
   - `DiffViewer.tsx` — renders unified diff with syntax highlighting (plain `<pre>` is acceptable for Phase 1)
   - `ContributionSummary.tsx` — renders the summary card from the plan doc (WHAT/WHY/VERIFY sections)
5. Create `backend/tests/test_pr_generator.py`
6. Run all tests

**Relevant Context:**
- `repository_manager.get_diff()` from Sprint 1 provides the raw diff
- `repository_manager.commit_all()` from Sprint 1 handles the actual commit
- GitHub PR creation (calling `POST /repos/{owner}/{repo}/pulls`) is explicitly out of scope for Phase 1 — the PR draft is markdown only

**Status:** `[x] done`

---

## Sprint 6 — Frontend Contribution Workflow + Demo Polish

**Intent:** Connect all backend endpoints to a usable frontend flow. The user must be able to go from "Analyze repo" → "Find issues" → "Pick issue" → "Approve plan" → "See results" without leaving the browser.

**Expected Outcomes:**
- New **Contribute** tab visible on the dashboard for `ready` projects
- Full flow navigable: issue list → issue detail → plan approval → verification progress → diff + commit → PR draft
- Session metrics summary card shown at the end
- No automatic external actions — every push/PR requires a button click

**Todo List:**
1. Add `'contribute'` to the `Tab` type and `TABS` array in `DashboardPage.tsx`
2. Create `frontend/src/pages/ContributePage.tsx` — state machine mirror of the backend orchestrator states
3. Create `frontend/src/components/IssueList.tsx` — renders issues with suitability reasons (checkmarks and concern icons, no scores)
4. Create `frontend/src/components/ContributionPlan.tsx` — renders ordered plan steps with `[Approve Plan]` button
5. Create `frontend/src/components/VerificationLoop.tsx` — shows attempt-by-attempt test results
6. Create `frontend/src/components/DiffViewer.tsx` — `<pre>` block with unified diff
7. Create `frontend/src/components/ContributionSummary.tsx` — final summary card
8. Extend `frontend/src/api/client.ts` with all new contribution endpoints
9. Extend `frontend/src/types/knowledge.ts` with `IssueAnalysis`, `ContributionPlan`, `SessionMetrics`, `ContributionSummary` types
10. Add `GITHUB_TOKEN` to `docker-compose.yml` as optional env var on the backend service
11. Run `npm run build` inside frontend — no TypeScript errors
12. Run full backend test suite — all passing

**Relevant Context:**
- Do not add external UI component libraries — keep the existing CSS variable system
- The `[Approve Plan]` button must call `POST /projects/{id}/contribute/execute` — no execution before this
- The `[Create Draft PR]` button calls `GET /projects/{id}/contribute/pr-draft` and opens a modal with the markdown
- The `[Commit Changes]` button calls `POST /projects/{id}/contribute/commit` with the editable commit message

**Status:** `[x] done`

---

## Safety Constraints (apply to all sprints)

These are non-negotiable across every sprint:

| Action | Policy |
|---|---|
| `git push` | ❌ Never automatic — requires explicit user POST |
| GitHub PR creation | ❌ Not in Phase 1 — draft markdown only |
| `pip install` / `npm install` | ❌ Never executed inside analysis |
| `rm -rf` or destructive shell commands | ❌ Never executed |
| Repository code execution | ❌ Never — analysis is read-only |
| Merge / rebase / force-push | ❌ Never |
| Changes to CI/CD or secrets | ❌ Never |
| Test suite execution timeout | ✅ Hard cap: 120 seconds |
| Fix loop cap | ✅ `MAX_FIX_ATTEMPTS = 3` |

---

## What is explicitly out of scope for Phase 1

- LLM-driven code modification (the implementation step is a stub in Sprint 4)
- Multi-language support beyond what the analyzer already detects
- Autonomous issue selection (user always picks)
- GitHub PR API calls (draft is markdown only)
- Multi-repo workspaces
- Deployment or infrastructure changes
- Numerical issue scoring

---

## Definition of Done

The plan is complete when all of these are true:

- All 6 sprints have `[x] done` status
- Full backend test suite passes (`pytest -v`)
- Frontend builds without TypeScript errors (`npm run build`)
- The demo flow works end-to-end from a fresh `docker compose up --build`:
  1. User submits a GitHub repo URL → analysis completes
  2. User clicks **Contribute** → sees open issues with suitability reasons
  3. User picks an issue → sees a contribution plan
  4. User clicks **Approve Plan** → orchestrator runs (stub implementation)
  5. User sees verification results
  6. User sees diff, edits commit message, clicks **Commit Changes**
  7. User sees PR draft markdown in a modal
  8. User sees session metrics summary
