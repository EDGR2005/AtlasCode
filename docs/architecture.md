# CodeAtlas Architecture

---

## Phase 1 — Codebase Intelligence (Complete)

```
React UI  (Vite + TypeScript + @xyflow/react)
    │  HTTP  (dev: Vite proxy  |  prod: nginx proxy_pass)
    ▼
FastAPI Backend                          :8000
    │
    ├── POST /projects/analyze  ──► BackgroundTask: run_pipeline()
    │                                       │
    │                               ┌───────▼──────────────────┐
    │                               │   Analyzer Pipeline       │
    │                               │  1. clone_repository      │
    │                               │  2. scan_files            │
    │                               │  3. detect_technologies   │
    │                               │  4. extract_dependencies  │
    │                               │  5. detect_relationships  │
    │                               │  6. detect_database_schema│
    │                               └──────────┬───────────────┘
    │                                          │ writes
    │                                          ▼
    └── GET /projects/{id}/*  ───► ProjectStorage  ──► projects/<id>/
                                                         metadata.json
                                                         knowledge.json
                                                         repository/  (git clone)

MCP Server  (separate stdio process)
    └── instantiates ProjectStorage(projects/)
        reads knowledge.json directly — no FastAPI import
```

### Phase 1 components

- FastAPI backend (process 1) — `app/main.py`
- MCP stdio server (process 2) — `app/mcp/server.py`
- React frontend — `frontend/src/`
- Filesystem project storage — `projects/`
- Analysis pipeline — `app/analyzer/`
- Knowledge models — `app/knowledge/models.py`

---

## Phase 2 — Contribution Agent (In Progress)

Phase 2 adds a contribution workflow on top of the Phase 1 knowledge model. The architecture is additive — no Phase 1 components are modified or replaced.

```
React UI
    │
    ├── Dashboard (Phase 1 tabs: Overview, Tech, Deps, Architecture, Repository, Database)
    │
    └── Contribute tab (Phase 2)
              │
              ▼
    FastAPI Backend  :8000
              │
    ┌─────────┴──────────────────────────────────────────────────┐
    │  /projects/{id}/contribute/*  (new router)                  │
    │                                                             │
    │  POST /contribute/issues   ──► github.client               │
    │                                    └── github.issue_analyzer│
    │                                                             │
    │  POST /contribute/plan     ──► contribution.issue_mapper   │
    │                                    └── contribution.plan_generator
    │                                                             │
    │  POST /contribute/execute  ──► BackgroundTask              │
    │                                    └── contribution.orchestrator
    │                                          │                  │
    │                                   BRANCHING                 │
    │                                    ↓                        │
    │                               IMPLEMENTING (stub)           │
    │                                    ↓                        │
    │                                TESTING ──► test_runner     │
    │                                    ↓                        │
    │                          DONE or FIXING (max 3)            │
    │                                                             │
    │  GET  /contribute/diff     ──► repository_manager.get_diff │
    │  POST /contribute/commit   ──► repository_manager.commit_all
    │  GET  /contribute/summary  ──► session.load_metrics        │
    │  GET  /contribute/pr-draft ──► pr_generator                │
    └─────────────────────────────────────────────────────────────┘
              │
              ▼
    projects/<id>/
        metadata.json       (Phase 1)
        knowledge.json      (Phase 1)
        session.json        (Phase 2 — new)
        repository/         git clone
            └── atlas/<issue>-<slug>  ← isolated contribution branch
```

### Phase 2 new modules

| Module | Responsibility |
|---|---|
| `app/github/client.py` | Fetch open issues via GitHub REST API |
| `app/github/issue_analyzer.py` | Classify issues: type, scope, reasons, concerns |
| `app/contribution/repository_manager.py` | Git branch / diff / commit (wraps GitPython) |
| `app/contribution/issue_mapper.py` | Issue keywords → relevant file list |
| `app/contribution/plan_generator.py` | Generate `ContributionPlan` struct |
| `app/contribution/test_runner.py` | Detect + run test suite (subprocess, 120s timeout) |
| `app/contribution/orchestrator.py` | State machine: BRANCH → IMPLEMENT → TEST → FIX |
| `app/contribution/session.py` | Persist `SessionMetrics` to `session.json` |
| `app/contribution/pr_generator.py` | Commit message + PR draft markdown |
| `app/api/contribution.py` | FastAPI router for all `/contribute/*` endpoints |

### Safety boundary

```
NEVER automatic:
  git push
  GitHub PR creation
  pip install / npm install
  rm -rf or any destructive command
  Execution of repository code

ALWAYS requires explicit user action:
  commit  →  POST /contribute/commit
  PR      →  user copies markdown draft
```

---

## On-disk layout (combined Phase 1 + 2)

```
projects/
└── <project_id>/
    ├── metadata.json       project status, name, created_at
    ├── knowledge.json      full ProjectKnowledge (Phase 1)
    ├── session.json        SessionMetrics for active contribution (Phase 2)
    └── repository/         git clone (shallow, depth=1)
        └── (working tree)  may have atlas/* branch checked out
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PROJECTS_DIR` | `../projects` | Shared between FastAPI and MCP server |
| `GITHUB_TOKEN` | _(empty)_ | Optional — raises GitHub API rate limit to 5000 req/h |
