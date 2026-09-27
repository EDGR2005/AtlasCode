# CodeAtlas — Summary

> **Map any codebase. Understand any issue. Make your first contribution.**

CodeAtlas is an MCP-powered codebase intelligence platform. It does not contain an LLM — it produces structured, evidence-backed knowledge that an external AI agent consumes, and (in Phase 2) guides users through making their first Open Source contribution.

---

## Phases

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Read-only analysis: technologies, dependencies, architecture, DB schema, MCP tools | ✅ Complete |
| **Phase 2** | Contribution agent: issue discovery, code mapping, branch management, test loop, PR draft | 🔄 In progress |
| **Phase 3** | Push + PR API, LLM-assisted implementation, multi-repo, PostgreSQL backend | ⬜ Planned |

---

## Project Structure

```
AtlasCode/
├── backend/
│   ├── app/
│   │   ├── main.py                     FastAPI app + CORS + /health
│   │   ├── dependencies.py             ProjectStorage DI factory (PROJECTS_DIR env var)
│   │   ├── api/
│   │   │   ├── projects.py             8 REST endpoints (Phase 1)
│   │   │   └── contribution.py         Contribution workflow endpoints (Phase 2)
│   │   ├── analyzer/
│   │   │   ├── repository.py           GitPython shallow clone (depth=1)
│   │   │   ├── files.py                File tree scanner, marks manifests as important
│   │   │   ├── technologies.py         Detects 14+ technologies from manifests + extensions
│   │   │   ├── dependencies.py         Extracts deps from npm/pypi/cargo/go manifests
│   │   │   ├── relationships.py        Regex import scanner (Python + TS/JS), inferred=True
│   │   │   ├── database.py             SQL/SQLAlchemy/Django/Prisma schema parser
│   │   │   └── pipeline.py             Orchestrator: clone → scan → detect → save → ready
│   │   ├── github/                     (Phase 2)
│   │   │   ├── client.py               GitHub REST API wrapper (httpx)
│   │   │   └── issue_analyzer.py       Issue suitability: reasons + concerns, no scores
│   │   ├── contribution/               (Phase 2)
│   │   │   ├── repository_manager.py   Git branch / diff / commit
│   │   │   ├── issue_mapper.py         Issue keywords → relevant files
│   │   │   ├── plan_generator.py       ContributionPlan struct
│   │   │   ├── test_runner.py          Run test suite (subprocess, 120s timeout)
│   │   │   ├── orchestrator.py         State machine: BRANCH→IMPLEMENT→TEST→FIX
│   │   │   ├── session.py              SessionMetrics → session.json
│   │   │   └── pr_generator.py         Commit message + PR draft markdown
│   │   ├── knowledge/
│   │   │   ├── models.py               Pydantic v2 models (Phase 1 + Phase 2)
│   │   │   └── storage.py              Filesystem JSON abstraction (swappable)
│   │   └── mcp/
│   │       ├── server.py               Standalone stdio MCP server, 6 tools
│   │       └── __main__.py             Entry: python -m app.mcp
│   ├── tests/                          55+ tests, all offline, all passing
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── types/knowledge.ts          TypeScript types mirroring Pydantic models
│   │   ├── api/client.ts               Typed fetch wrappers
│   │   ├── App.tsx                     React Router: / and /projects/:id
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx         URL input + analyze + navigate
│   │   │   ├── DashboardPage.tsx       6-tab dashboard with 2s polling
│   │   │   └── ContributePage.tsx      Contribution workflow UI (Phase 2)
│   │   └── components/
│   │       ├── OverviewPanel.tsx
│   │       ├── TechnologiesPanel.tsx   Cards with evidence source + confidence bar
│   │       ├── DependenciesPanel.tsx   Grouped by ecosystem
│   │       ├── RepositoryPanel.tsx     Collapsible file tree
│   │       ├── ArchitectureGraph.tsx   React Flow graph, dashed edges for inferred
│   │       ├── DatabasePanel.tsx       React Flow DB schema diagram
│   │       ├── IssueList.tsx           Issue suitability cards (Phase 2)
│   │       ├── ContributionPlan.tsx    Plan steps + Approve button (Phase 2)
│   │       ├── VerificationLoop.tsx    Test attempt results (Phase 2)
│   │       ├── DiffViewer.tsx          Unified diff viewer (Phase 2)
│   │       └── ContributionSummary.tsx Final summary card (Phase 2)
│   ├── Dockerfile
│   ├── nginx.conf                      Proxies /projects + /health → backend, SPA fallback
│   └── vite.config.ts                  Dev proxy to :8000
├── projects/                           Runtime: cloned repos + knowledge files
├── examples/fixtures/                  Offline test fixtures
├── docs/
│   ├── architecture.md                 Full architecture (Phase 1 + 2)
│   ├── contribution-agent.md           Phase 2 spec (models, endpoints, state machine)
│   └── summaryAtlasCode.md             This file
├── atlas-contribution-agent-plan.md    Sprint-by-sprint implementation plan
├── docker-compose.yml
└── README.md
```

---

## How to Run

### Docker (recommended)

```bash
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |

Optional — set a GitHub token to avoid rate limits (Phase 2):

```bash
export GITHUB_TOKEN=ghp_yourtoken
docker compose up --build
```

### Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Run tests

```bash
cd backend
.venv/bin/python -m pytest -v
```

---

## REST API

### Phase 1 — Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/projects/analyze` | Submit a GitHub URL for analysis |
| GET | `/projects/` | List all analyzed projects |
| GET | `/projects/{id}` | Project summary + status |
| GET | `/projects/{id}/tree` | Repository file tree |
| GET | `/projects/{id}/technologies` | Detected technologies with evidence |
| GET | `/projects/{id}/dependencies` | Direct dependencies by ecosystem |
| GET | `/projects/{id}/architecture` | Components and relationships |
| GET | `/projects/{id}/database` | Detected database schema |

### Phase 2 — Contribution

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/contribute/issues` | Fetch + analyze GitHub issues |
| POST | `/projects/{id}/contribute/plan` | Body: `{issue_number}` → `ContributionPlan` |
| POST | `/projects/{id}/contribute/execute` | Start contribution loop (background task) |
| GET | `/projects/{id}/contribute/status` | Orchestrator state + verification attempts |
| GET | `/projects/{id}/contribute/diff` | Current unified diff string |
| POST | `/projects/{id}/contribute/commit` | Body: `{message}` → stage + commit |
| GET | `/projects/{id}/contribute/summary` | `ContributionSummary` when DONE |
| GET | `/projects/{id}/contribute/pr-draft` | PR markdown (no GitHub API call) |

---

## MCP Tools (Phase 1)

The MCP server runs as a **separate `stdio` process** from FastAPI. Both read from the same `projects/` directory.

```bash
cd backend
source .venv/bin/activate
PROJECTS_DIR=../projects python -m app.mcp
```

| Tool | Arguments | Description |
|------|-----------|-------------|
| `get_project_overview` | `project_id` | Metadata, tech names, counts |
| `get_repository_tree` | `project_id` | File list with sizes and extensions |
| `get_tech_stack` | `project_id` | Technologies with version, source, confidence |
| `get_dependencies` | `project_id` | Dependencies grouped by ecosystem |
| `get_architecture` | `project_id` | Components and relationships |
| `search_code` | `project_id, query` | Bounded grep (max 500 files, 50 matches) |

---

## Knowledge Model

Every detected fact has a traceable `source` and `confidence` score.

```json
{
  "metadata": { "project_id": "...", "name": "...", "status": "ready", "created_at": "..." },
  "repository": { "url": "...", "default_branch": "main", "commit_sha": "..." },
  "technologies": [
    { "name": "TypeScript", "version": "5.4.5", "source": "package.json", "confidence": 1.0 }
  ],
  "dependencies": [
    { "name": "express", "version": "^4.19.2", "ecosystem": "npm", "source": "package.json" }
  ],
  "files": [
    { "path": "src/index.ts", "size_bytes": 128, "extension": ".ts", "is_important": false }
  ],
  "components": [],
  "relationships": [
    {
      "from_component": "src/controllers/UserController.ts",
      "to_component": "src/services/UserService.ts",
      "type": "imports",
      "confidence": 0.6,
      "inferred": true
    }
  ],
  "database": {
    "detected": true,
    "tables": [{ "name": "users", "columns": [...], "source_type": "sqlalchemy" }],
    "relationships": []
  }
}
```

---

## Technology Detection

| Manifest | Detects |
|----------|---------|
| `package.json` | Node.js, JavaScript, TypeScript, React, Next.js, Express |
| `pyproject.toml` | Python, FastAPI, Django, Flask |
| `requirements.txt` | Python, FastAPI, Django, Flask |
| `go.mod` | Go (with version) |
| `Cargo.toml` | Rust |
| `Dockerfile` | Docker, Python, Node.js |
| `.github/workflows/` | GitHub Actions |
| File extensions | Python, TypeScript, JavaScript, Java, Go, Rust (confidence 0.7) |

## Database Schema Detection

| Source | Detects |
|--------|---------|
| `.sql` files | CREATE TABLE, columns, PKs, FKs |
| `schema.prisma` | Prisma models, relations |
| Python (SQLAlchemy) | `Base`/`DeclarativeBase` subclasses, `Column`, `ForeignKey`, `relationship` |
| Python (Django ORM) | `models.Model` subclasses, all field types, `ForeignKey`, `ManyToManyField` |

---

## Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Filesystem JSON | No DB dependency in Phase 1–2; `ProjectStorage` interface is swappable |
| Analysis trigger | FastAPI `BackgroundTasks` | No Celery/Redis needed |
| MCP transport | `stdio` | Matches Bob's MCP client |
| MCP process model | Separate from FastAPI | No shared memory; both read `projects/` from disk |
| Clone strategy | `depth=1` shallow clone | Faster — only latest commit needed for static analysis |
| Relationship detection | Regex import scanning | `inferred=True`; AST over-engineered for Phase 1 |
| Branch naming | `atlas/{issue}-{slug}` | Clearly namespaced, avoids conflicts with user branches |
| PR strategy | Markdown draft only | User retains full control; no automatic push |
| Fix loop cap | `MAX_FIX_ATTEMPTS = 3` | Prevents infinite loops; keeps session bounded |
| Test timeout | 120 seconds | Prevents hangs on large suites |
| Frontend build | Vite + React + TypeScript | Fast dev loop; lean bundle |
| Graph library | `@xyflow/react` | Handles pan/zoom/select for both architecture + DB diagrams |

---

## Test Coverage

### Phase 1 (existing)

| Test file | Tests | Covers |
|-----------|-------|--------|
| `test_knowledge_models.py` | 6 | Model construction, validation, JSON round-trip |
| `test_storage.py` | 8 | Create/read/update/list/save/load |
| `test_analyzer_files.py` | 5 | File scanner, manifest tagging, skip dirs |
| `test_analyzer_technologies.py` | 8 | Tech detection from Python and Node fixtures |
| `test_analyzer_dependencies.py` | 5 | Dependency extraction from manifests |
| `test_analyzer_relationships.py` | 5 | Import relationship detection |
| `test_analyzer_database.py` | — | SQL/SQLAlchemy/Django/Prisma parsers |
| `test_api.py` | 9 | All REST endpoints, 404 handling |
| `test_mcp.py` | 9 | All 6 MCP tools, search_code safety |

### Phase 2 (in progress)

| Test file | Covers |
|-----------|--------|
| `test_repository_manager.py` | Branch, diff, commit — offline via `tmp_path` |
| `test_github_client.py` | Issue fetching — mocked httpx |
| `test_issue_analyzer.py` | Reason/concern detection, scope/type |
| `test_issue_mapper.py` | Keyword extraction, file relevance |
| `test_plan_generator.py` | Plan step generation |
| `test_test_runner.py` | Command detection, subprocess mock, timeout |
| `test_orchestrator.py` | State machine transitions |
| `test_pr_generator.py` | Commit message, PR template |
| `test_session.py` | SessionMetrics persistence |

All tests offline — zero network calls.

---

## Current Limitations (Phase 1)

- **Component detection**: `components` list is always empty — relationships are file-to-file only
- **No re-analysis**: no `reanalyze` endpoint yet
- **No search in REST API**: `search_code` is MCP-only
- **Fixed polling**: 2-second interval — no WebSocket/SSE push
- **No authentication**: single-user local tool only

## Fixes Applied

| Fix | File | Description |
|-----|------|-------------|
| DB diagram blank canvas | `DatabasePanel.tsx`, `index.css` | `ReactFlowProvider` + `onInit` deferred `fitView`; `min-height: 0` on `.dash-content` |
| Slow clone | `analyzer/repository.py` | Added `depth=1` to `git.Repo.clone_from()` |

---

## Further Reading

- [`docs/architecture.md`](architecture.md) — Full system architecture (Phase 1 + 2)
- [`docs/contribution-agent.md`](contribution-agent.md) — Phase 2 spec: models, endpoints, state machine, safety constraints
- [`atlas-contribution-agent-plan.md`](../atlas-contribution-agent-plan.md) — Sprint-by-sprint implementation plan with status tracking
- [`README.md`](../README.md) — Quick start and user-facing documentation
