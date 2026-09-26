# CodeAtlas — Phase 1 Summary

> **Map any codebase. Understand any issue.**

CodeAtlas is an MCP-powered codebase intelligence layer that gives AI coding agents structured context about unfamiliar repositories. It does not contain an LLM — it produces structured, evidence-backed knowledge that an external AI agent consumes.

---

## What Was Built

A complete working vertical slice:

```
Enter GitHub URL → Analyze → Generate Project Knowledge → Dashboard → MCP tools
```

---

## Project Structure

```
AtlasCode/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app + CORS + /health
│   │   ├── dependencies.py         ProjectStorage DI factory (PROJECTS_DIR env var)
│   │   ├── api/projects.py         7 REST endpoints
│   │   ├── analyzer/
│   │   │   ├── repository.py       GitPython clone → returns commit SHA
│   │   │   ├── files.py            File tree scanner, marks manifests as important
│   │   │   ├── technologies.py     Detects 14+ technologies from manifests + extensions
│   │   │   ├── dependencies.py     Extracts deps from npm/pypi/cargo/go manifests
│   │   │   ├── relationships.py    Regex import scanner (Python + TS/JS), all inferred=True
│   │   │   └── pipeline.py         Orchestrator: clone → scan → detect → save → ready
│   │   ├── knowledge/
│   │   │   ├── models.py           Pydantic v2 models with source + confidence on every fact
│   │   │   └── storage.py          Filesystem JSON abstraction (swappable interface)
│   │   └── mcp/
│   │       ├── server.py           Standalone stdio MCP server, 6 tools
│   │       └── __main__.py         Entry: python -m app.mcp
│   ├── tests/                      55 tests, all offline, all passing
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── types/knowledge.ts      TypeScript types mirroring Pydantic models
│   │   ├── api/client.ts           Typed fetch wrappers
│   │   ├── App.tsx                 React Router: / and /projects/:id
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx     URL input + analyze + navigate
│   │   │   └── DashboardPage.tsx   5-tab dashboard with 2s polling
│   │   └── components/
│   │       ├── OverviewPanel.tsx
│   │       ├── TechnologiesPanel.tsx   Cards with evidence source + confidence bar
│   │       ├── DependenciesPanel.tsx   Grouped by ecosystem
│   │       ├── RepositoryPanel.tsx     Collapsible file tree
│   │       └── ArchitectureGraph.tsx   React Flow graph, dashed edges for inferred
│   ├── Dockerfile
│   ├── nginx.conf                  Proxies /projects + /health → backend, SPA fallback
│   └── vite.config.ts              Dev proxy to :8000
├── projects/.gitkeep
├── examples/fixtures/
│   ├── sample-python-project/      pyproject.toml, requirements.txt, 3 .py files
│   └── sample-node-project/        package.json, 3 .ts files
├── docs/
│   ├── architecture.md
│   └── summaryAtlasCode.md         (this file)
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
# 55 passed, 0 network calls
```

---

## REST API

| Method | Endpoint                              | Description                              |
|--------|---------------------------------------|------------------------------------------|
| GET    | `/health`                             | Health check                             |
| POST   | `/projects/analyze`                   | Submit a GitHub URL for analysis         |
| GET    | `/projects/`                          | List all analyzed projects               |
| GET    | `/projects/{id}`                      | Project summary + status                 |
| GET    | `/projects/{id}/tree`                 | Repository file tree                     |
| GET    | `/projects/{id}/technologies`         | Detected technologies with evidence      |
| GET    | `/projects/{id}/dependencies`         | Direct dependencies by ecosystem         |
| GET    | `/projects/{id}/architecture`         | Components and relationships             |

`POST /projects/analyze` accepts:

```json
{ "repository_url": "https://github.com/owner/repo" }
```

Returns immediately with `project_id` and `status: "analyzing"`. Analysis runs as a background task.

---

## MCP Tools

The MCP server runs as a **separate `stdio` process** from FastAPI. Both processes independently instantiate `ProjectStorage` pointing at the same `projects/` directory on disk. No shared memory.

Start the MCP server:

```bash
cd backend
source .venv/bin/activate
PROJECTS_DIR=../projects python -m app.mcp
```

| Tool | Arguments | Description |
|------|-----------|-------------|
| `get_project_overview` | `project_id` | Metadata, tech names, file/dep/tech counts |
| `get_repository_tree` | `project_id` | Full file list with sizes and extensions |
| `get_tech_stack` | `project_id` | Technologies with version, source, confidence |
| `get_dependencies` | `project_id` | Dependencies grouped by ecosystem |
| `get_architecture` | `project_id` | Components and relationships (inferred flag preserved) |
| `search_code` | `project_id, query` | Safe bounded grep across cloned repository |

### `search_code` safety constraints

- Skips: `.git/`, `node_modules/`, `.venv/`, `venv/`, `dist/`, `build/`, `__pycache__/`, `.tox/`
- Skips binary files (catches `UnicodeDecodeError`)
- Hard limits: 500 files scanned, 50 matches returned
- Never executes repository code — read-only `open()` only
- Returns: `{"matches": [{"file": "...", "line": N, "text": "..."}], "truncated": bool}`

---

## Project Knowledge Model

Every detected fact carries a traceable evidence source and confidence score.

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
  ]
}
```

`inferred: true` marks heuristic detections. `confidence` is always in the range `[0.0, 1.0]`. Versions are never invented — `null` when not found in a manifest.

---

## Technology Detection

Supported manifest sources:

| Manifest | Detects |
|----------|---------|
| `package.json` | Node.js, JavaScript, TypeScript, React, Next.js, Express |
| `pyproject.toml` | Python, FastAPI, Django, Flask |
| `requirements.txt` | Python, FastAPI, Django, Flask |
| `go.mod` | Go (with version) |
| `Cargo.toml` | Rust |
| `Dockerfile` | Docker, Python, Node.js |
| `.github/workflows/` | GitHub Actions |
| File extensions | Python, TypeScript, JavaScript, Java, Go, Rust (fallback, confidence 0.7) |

---

## Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Filesystem JSON | No DB dependency in Phase 1; `ProjectStorage` interface is swappable |
| Analysis trigger | FastAPI `BackgroundTasks` | No Celery or Redis needed for Phase 1 |
| MCP transport | `stdio` | Matches Bob's MCP client; simplest transport |
| MCP process model | Separate process from FastAPI | No shared memory; both read `projects/` from disk |
| Relationship detection | Regex import scanning | Correctly flagged `inferred=True`; AST is over-engineered for Phase 1 |
| `search_code` safety | Blocked dirs + file cap + match cap | Never executes code; bounded to prevent hang on large repos |
| Frontend build | Vite + React + TypeScript | Fast dev loop; lean bundle |
| Graph library | `@xyflow/react` | Specified; handles pan/zoom/select out of the box |
| Clone tool | GitPython | Cleaner API than subprocess; easy to mock in tests |

---

## Test Coverage

| Test file | Tests | Covers |
|-----------|-------|--------|
| `test_knowledge_models.py` | 6 | Model construction, validation, JSON round-trip |
| `test_storage.py` | 8 | Create/read/update/list/save/load via `tmp_path` |
| `test_analyzer_files.py` | 5 | File scanner, manifest tagging, skip dirs |
| `test_analyzer_technologies.py` | 8 | Tech detection from Python and Node fixtures |
| `test_analyzer_dependencies.py` | 5 | Dependency extraction from manifests |
| `test_analyzer_relationships.py` | 5 | Import relationship detection, inferred=True |
| `test_api.py` | 9 | All REST endpoints, 404 handling, background task mock |
| `test_mcp.py` | 9 | All 6 MCP tools, search_code safety, truncation |
| **Total** | **55** | **All offline — zero network calls** |

---

## Current Limitations

- **Component detection**: `components` list is always empty in Phase 1. Relationships are file-to-file only.
- **No re-analysis**: once analyzed, there is no "re-analyze" endpoint or button yet.
- **No search in REST API**: `search_code` is only available via MCP.
- **Analysis polling**: 2-second fixed interval; no WebSocket/SSE push.
- **Large repos**: file tree returns all files without pagination.
- **Code Graph tab**: shares the Architecture view (React Flow graph).
- **No authentication**: any caller can submit any public GitHub URL.

---

## Recommended Next Steps (Phase 2)

In priority order:

1. **Re-analysis** — `POST /projects/{id}/reanalyze` endpoint + UI button
2. **Component detection** — classify files by role (controller/service/model/repository) using path heuristics and decorator/annotation scanning
3. **REST search endpoint** — expose `search_code` through the REST API
4. **Analysis progress streaming** — replace polling with WebSocket or SSE
5. **Issue analysis** — accept an issue description, map it to relevant files via the knowledge model, return a focused context package for the AI agent

---

## Out of Scope (Phase 1)

- Issue analysis or autonomous code modification
- AST-based deep analysis
- Authentication or multi-user support
- PostgreSQL, Redis, Neo4j, Celery, Kubernetes
- LLM integration of any kind
- Execution of any repository code (`npm install`, `pip install`, `make`, `docker build`, etc.)
