# AtlasCode — Contribution Agent (Phase 2)

> **Vision:** "Your first contribution to Open Source, guided from issue to pull request."

Phase 2 transforms AtlasCode from a read-only codebase intelligence tool into an interactive **contribution agent** — a mentor + developer assistant that guides a user through the complete lifecycle of making a first Open Source contribution, from finding a suitable issue all the way to a ready-to-publish pull request.

---

## What Phase 2 Adds

| Capability | Phase 1 | Phase 2 |
|---|---|---|
| Analyze repository structure | ✅ | ✅ |
| Detect technologies / dependencies | ✅ | ✅ |
| Database schema visualization | ✅ | ✅ |
| Fetch GitHub issues | ❌ | ✅ |
| Classify issue suitability (no scores) | ❌ | ✅ |
| Map issue to relevant files | ❌ | ✅ |
| Generate contribution plan | ❌ | ✅ |
| Create isolated Git branch | ❌ | ✅ |
| Run test suite + loop on failures | ❌ | ✅ |
| Generate commit message | ❌ | ✅ |
| Generate PR draft (markdown) | ❌ | ✅ |
| Session metrics | ❌ | ✅ |
| Mentor mode (explain each step) | ❌ | ✅ |

---

## User Flow

```
User: "Help me make my first contribution."
         ↓
AtlasCode fetches open GitHub issues
         ↓
Classifies which are approachable (reasons, not scores)
         ↓
User picks an issue
         ↓
AtlasCode maps issue text → relevant files in the cloned repo
         ↓
Generates a contribution plan (user must approve)
         ↓
[Approve Plan] button clicked
         ↓
Creates isolated branch: atlas/<issue>-<slug>
         ↓
Implementation step (stub in Phase 2 / AI-assisted in Phase 3)
         ↓
Runs test suite (up to 3 attempts on failure)
         ↓
User reviews diff
         ↓
User edits and approves commit message → commit
         ↓
User views PR draft markdown → [Create Draft PR]
         ↓
Session metrics summary shown
```

Nothing is pushed to GitHub automatically. Every external action requires an explicit user button press.

---

## Architecture

### New Backend Modules

```
backend/app/
├── github/
│   ├── __init__.py
│   ├── client.py           GitHub REST API wrapper (httpx, token via env var)
│   └── issue_analyzer.py   Suitability analysis — reasons only, no scores
│
├── contribution/
│   ├── __init__.py
│   ├── repository_manager.py   Git branch / diff / commit (wraps GitPython)
│   ├── issue_mapper.py         Issue keywords → ranked relevant files
│   ├── plan_generator.py       Produces ContributionPlan struct
│   ├── test_runner.py          Runs test suite via subprocess (120s timeout)
│   ├── session.py              Records SessionMetrics to session.json
│   ├── orchestrator.py         State machine: BRANCH→IMPLEMENT→TEST→(FIX→TEST)*
│   └── pr_generator.py         Commit message + PR draft markdown
│
└── api/
    ├── projects.py             (unchanged)
    └── contribution.py         New FastAPI router: /projects/{id}/contribute/*
```

### New Frontend Components

```
frontend/src/
├── pages/
│   └── ContributePage.tsx          Full contribution workflow (mirrors backend states)
└── components/
    ├── IssueList.tsx               Issues with suitability reasons + concern flags
    ├── IssueSuitability.tsx        Per-issue detail: reasons, concerns, scope, type
    ├── ContributionPlan.tsx        Ordered steps + [Approve Plan] button
    ├── VerificationLoop.tsx        Attempt-by-attempt test results
    ├── DiffViewer.tsx              Unified diff viewer (<pre> block)
    └── ContributionSummary.tsx     Final summary card (WHAT/WHY/WHERE/VERIFY)
```

### New REST Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/{id}/contribute/issues` | Fetch + analyze GitHub issues for this project |
| `POST` | `/projects/{id}/contribute/plan` | Body: `{issue_number}` → returns `ContributionPlan` |
| `POST` | `/projects/{id}/contribute/execute` | Starts the contribution loop (background task) |
| `GET` | `/projects/{id}/contribute/status` | Current orchestrator state + verification attempts |
| `GET` | `/projects/{id}/contribute/diff` | Current unified diff string |
| `POST` | `/projects/{id}/contribute/commit` | Body: `{message}` → stages + commits, returns SHA |
| `GET` | `/projects/{id}/contribute/summary` | `ContributionSummary` when session is DONE |
| `GET` | `/projects/{id}/contribute/pr-draft` | PR markdown string (no GitHub API call) |

---

## New Knowledge Models

Added to `backend/app/knowledge/models.py`:

### `IssueAnalysis`

```python
class IssueAnalysis(BaseModel):
    issue_number: int
    title: str
    type: str                  # "bug" | "docs" | "feature" | "refactor" | "unknown"
    scope: str                 # "small" | "medium" | "large" | "unknown"
    reasons: list[str]         # positive signals e.g. "Problem is clearly described"
    concerns: list[str]        # risk signals e.g. "No reproduction steps provided"
    labels: list[str]
    url: str
```

### `RelevantFile`

```python
class RelevantFile(BaseModel):
    path: str
    reason: str         # e.g. "Issue mentions 'validate_token' — found in this file"
    inferred: bool = True
```

### `ContributionStep` / `ContributionPlan`

```python
class ContributionStep(BaseModel):
    index: int
    description: str    # plain-language sentence

class ContributionPlan(BaseModel):
    issue_number: int
    branch_name: str            # e.g. "atlas/123-fix-validation"
    relevant_files: list[RelevantFile]
    steps: list[ContributionStep]
    approved: bool = False
```

### `TestResult` / `VerificationAttempt`

```python
class TestResult(BaseModel):
    passed: int
    failed: int
    errors: int
    output: str         # raw stdout/stderr (truncated to 4000 chars)
    duration_seconds: float
    timed_out: bool = False

class VerificationAttempt(BaseModel):
    attempt: int
    result: TestResult
```

### `SessionMetrics`

```python
class SessionMetrics(BaseModel):
    project_id: str
    issue_number: int
    branch_name: str
    state: str                          # orchestrator state
    files_analyzed: int = 0
    files_modified: int = 0
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    fix_attempts: int = 0
    attempts: list[VerificationAttempt] = []
    started_at: datetime
    finished_at: datetime | None = None
```

Persisted as `session.json` inside `projects/<project_id>/`.

### `ContributionSummary`

```python
class ContributionSummary(BaseModel):
    issue_number: int
    issue_title: str
    branch_name: str
    commit_sha: str | None
    diff_stat: str              # e.g. "2 files changed, 24 insertions(+), 5 deletions(-)"
    pr_draft: str               # markdown string
    metrics: SessionMetrics
```

---

## `repository_manager.py` — API

All functions take `clone_path: Path` (from `storage.get_clone_path(project_id)`).

| Function | Description |
|---|---|
| `get_repo(clone_path)` | Returns `git.Repo` instance |
| `create_branch(clone_path, branch_name)` | Creates and checks out branch |
| `get_current_branch(clone_path)` | Returns current branch name string |
| `get_status(clone_path)` | Returns list of modified/untracked file paths |
| `get_diff(clone_path)` | Returns unified diff string (`git diff HEAD`) |
| `commit_all(clone_path, message)` | Stages all tracked changes and commits |

Branch naming convention: `atlas/{issue_number}-{slug}`
Example: `atlas/123-fix-expired-token`

---

## `issue_analyzer.py` — Suitability Signals

**Positive signals (added to `reasons`):**
- Label matches: `good first issue`, `help wanted`, `easy`, `beginner`, `documentation`, `bug`, `small`
- Title is short and descriptive (< 80 chars)
- Body clearly describes expected vs actual behavior
- Body mentions reproduction steps
- Body length suggests focused scope (200–1500 chars)

**Concern signals (added to `concerns`):**
- No description in body
- Body references many unrelated files/modules
- Labels suggest complexity: `breaking change`, `RFC`, `architecture`, `security`
- Issue has no comments (may be abandoned)
- Body is very long (> 3000 chars) — may indicate high complexity

**Scope estimation:**
- `small` — body < 800 chars, labels hint small, title < 60 chars
- `large` — body > 2500 chars, or labels hint breaking/architecture
- `medium` — everything else
- `unknown` — no body

**No numerical scores are ever shown to the user.**

---

## `orchestrator.py` — State Machine

```
IDLE
  ↓  [POST /contribute/execute]
BRANCHING
  ↓  branch created
IMPLEMENTING
  ↓  changes applied (stub in Phase 2)
TESTING
  ↓  test suite run
  ├── PASS → DONE
  └── FAIL → FIXING (if attempts < MAX_FIX_ATTEMPTS)
               ↓
            IMPLEMENTING
               ↓
            TESTING
               └── FAIL (attempts == MAX_FIX_ATTEMPTS) → FAILED
```

- `MAX_FIX_ATTEMPTS = 3`
- State is persisted to `session.json` on every transition
- No automatic `git push` at any state
- `DONE` and `FAILED` are terminal states

---

## `test_runner.py` — Test Command Detection

| Technology detected | Command tried |
|---|---|
| Python + pytest in deps | `python -m pytest -v` |
| Python (no pytest) | `python -m unittest discover` |
| Node.js + `test` script in package.json | `npm test` |
| Rust | `cargo test` |
| Go | `go test ./...` |

- Hard timeout: **120 seconds**
- Never runs: `pip install`, `npm install`, `cargo build`, `make`, or any install command
- Output truncated to 4000 characters before storage
- Returns `TestResult` with `timed_out=True` on timeout

---

## `pr_generator.py` — Output Formats

### Commit message (conventional commits)

```
fix(auth): reject expired tokens in validate_token()

Closes #123
```

Type is derived from `IssueAnalysis.type`:
- `bug` → `fix`
- `docs` → `docs`
- `feature` → `feat`
- `refactor` → `refactor`
- `unknown` → `chore`

### PR draft markdown template

```markdown
## Summary

<!-- one-sentence description of the change -->

## Problem

<!-- what the issue described -->

## Changes

- <!-- bullet per modified file with what changed -->

## Testing

- <!-- test command used -->
- <!-- result: N passed, 0 failed -->

## Related Issue

Closes #{issue_number}
```

---

## Safety Constraints

| Action | Policy |
|---|---|
| `git push` | ❌ Never automatic — explicit `POST /contribute/push` (Phase 3) |
| GitHub PR creation via API | ❌ Not in Phase 2 — draft markdown only |
| `pip install` / `npm install` | ❌ Never executed |
| Destructive shell commands (`rm -rf`, etc.) | ❌ Never executed |
| Repository code execution | ❌ Never — analysis is read-only |
| Merge / rebase / force-push | ❌ Never |
| CI/CD or secret file changes | ❌ Never |
| Test suite timeout | ✅ Hard cap: 120 seconds |
| Fix loop cap | ✅ `MAX_FIX_ATTEMPTS = 3` |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PROJECTS_DIR` | Yes | Path to projects directory (default: `../projects`) |
| `GITHUB_TOKEN` | No | GitHub personal access token — raises rate limit from 60 to 5000 req/hour |

Add to `docker-compose.yml`:

```yaml
backend:
  environment:
    - PROJECTS_DIR=/app/projects
    - GITHUB_TOKEN=${GITHUB_TOKEN:-}   # optional — set in host shell or .env
```

---

## Test Coverage (Phase 2 additions)

| Test file | Covers |
|---|---|
| `test_repository_manager.py` | Branch creation, diff, commit — all offline via `tmp_path` + `git.Repo.init()` |
| `test_github_client.py` | Issue fetching — mocked `httpx` responses, zero network |
| `test_issue_analyzer.py` | Reason/concern detection, scope/type classification |
| `test_issue_mapper.py` | Keyword extraction, file relevance scoring — offline fixture repos |
| `test_plan_generator.py` | Plan step generation, branch name formatting |
| `test_test_runner.py` | Command detection, subprocess mock, timeout handling |
| `test_orchestrator.py` | State machine transitions, attempt cap enforcement |
| `test_pr_generator.py` | Commit message format, PR markdown template |
| `test_session.py` | SessionMetrics persistence to/from `session.json` |

All tests are offline. Zero network calls.

---

## What is Out of Scope for Phase 2

- LLM-driven code modification (implementation step is a no-op stub)
- GitHub PR API (push + open PR) — Phase 3
- Multi-language support beyond Python, Node.js, Rust, Go
- Autonomous issue selection — user always picks
- Multi-repo workspaces
- Numerical issue scoring
- Authentication / multi-user
- Deployment or infrastructure changes

---

## Implementation Sprints

See [`atlas-contribution-agent-plan.md`](../atlas-contribution-agent-plan.md) for the full sprint-by-sprint implementation plan with todo lists and status tracking.

| Sprint | Scope | Status |
|---|---|---|
| Sprint 1 | Repository Manager (branch/diff/commit) | 🔄 In progress |
| Sprint 2 | GitHub Issue Analyzer (fetch + classify) | ⬜ Pending |
| Sprint 3 | Issue → Code Mapper + Plan Generator | ⬜ Pending |
| Sprint 4 | Coding Agent (test + fix loop) | ⬜ Pending |
| Sprint 5 | Commit + PR Draft Generator | ⬜ Pending |
| Sprint 6 | Frontend Contribution Workflow + Demo | ⬜ Pending |
