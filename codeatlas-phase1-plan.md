# CodeAtlas — Phase 1 Plan: Walking Skeleton

## Top-Level Overview

Build a working end-to-end vertical slice of **CodeAtlas** — an MCP-powered codebase intelligence platform.

The system lets a developer enter a public GitHub URL, triggers a read-only analysis pipeline, stores a structured Project Knowledge Model on disk, displays results in a React dashboard, and exposes the same knowledge through MCP tools that AI agents can consume.

**No LLM is built into CodeAtlas. No arbitrary repository code is executed.**
All detected facts must have a traceable evidence source.

---

## Architecture at a Glance

```
React UI (Vite + TypeScript + React Flow)
        │ HTTP REST
        ▼
FastAPI Backend  (process 1)
        │
   ┌────┼────────────────────────────────┐
   ▼    ▼                                ▼
Analyzer  Knowledge                 Filesystem
Pipeline   Model                   projects/<id>/
              │                      metadata.json
              │                      knowledge.json
              │                      repository/
              │                           ▲
              └───────────────────────────┘
                                          │
                              MCP Server (process 2 — stdio)
                              independently instantiates
                              ProjectStorage → same directory
```

**Key process model:** FastAPI and the MCP server are two separate processes.
Both instantiate `ProjectStorage(base_path)` pointing at the same `projects/` directory on disk.
They do NOT share in-memory state. The filesystem is the single source of truth.

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold & Tooling

**Status:** `[ ] pending`

**Intent**
Create the full directory skeleton and all tooling configuration files so every subsequent sub-task has a stable place to land. Nothing is implemented here beyond structure.

**Expected Outcomes**
- Directory tree matches the specification exactly.
- `backend/` has a working Python virtual environment definition (`pyproject.toml` or `requirements.txt`).
- `frontend/` has a working Vite + React + TypeScript scaffold.
- `docker-compose.yml` compiles and starts both containers (empty health-check endpoints are fine at this stage).
- `.gitignore` extended with `projects/`, `__pycache__/`, `.venv/`, `dist/`, `node_modules/`.

**Todo List**
1. Extend workspace-root `.gitignore` with `projects/*/repository/`, `.venv/`, and `projects/.gitkeep` exemption.
2. Create `backend/` with `pyproject.toml` (or `requirements.txt`), `Dockerfile`.
3. Create `backend/app/__init__.py` and `main.py` (FastAPI app with single health endpoint `GET /health`).
4. Create empty `__init__.py` files in `app/api/`, `app/analyzer/`, `app/knowledge/`, `app/mcp/`.
5. Create `backend/tests/__init__.py`.
6. Scaffold `frontend/` using Vite: `npm create vite@latest frontend -- --template react-ts`.
7. Install frontend deps: `@xyflow/react`, `react-router-dom`, no other heavy additions.
8. Create `frontend/Dockerfile`.
9. Create `projects/` with a `.gitkeep`.
10. Create `examples/fixtures/` with a `.gitkeep`.
11. Create `docs/` with an `architecture.md` stub.
12. Create `docker-compose.yml` at workspace root.

**Relevant Context**
- Workspace root IS the project root: `/home/edu-gar/Escritorio/AtlasCode`. Do NOT create a nested `codeatlas/` directory.
- Final top-level layout: `backend/`, `frontend/`, `projects/`, `examples/`, `docs/`, `docker-compose.yml`, `README.md`.
- Existing `.gitignore` already covers `node_modules/`, `venv/`, `dist/`, `build/`, `__pycache__/`.
- Must extend it with: `projects/*/repository/` (cloned repos must never be committed).

---

### Sub-Task 2 — Project Knowledge Model

**Status:** `[ ] pending`

**Intent**
Define the single source of truth for all structured repository data. Every other module (analyzer, REST API, MCP) reads or writes this model. Getting the types right here prevents coupling problems later.

**Expected Outcomes**
- `backend/app/knowledge/models.py` contains fully typed Pydantic v2 models.
- All detected facts carry `source: str` and `confidence: float` fields.
- The model serialises cleanly to/from JSON.
- Unit tests in `tests/test_knowledge_models.py` validate construction and round-trip serialisation.

**Todo List**
1. Define `TechnologyDetection(BaseModel)` with fields: `name`, `version: str | None`, `source`, `confidence`.
2. Define `Dependency(BaseModel)` with fields: `name`, `version: str | None`, `ecosystem`, `source`.
3. Define `FileEntry(BaseModel)` with fields: `path`, `size_bytes`, `extension`, `is_important: bool`.
4. Define `Component(BaseModel)` with fields: `name`, `path`, `type` (e.g. `"controller"`, `"service"`, `"module"`, `"unknown"`).
5. Define `Relationship(BaseModel)` with fields: `from_component`, `to_component`, `type` (e.g. `"imports"`), `confidence`, `inferred: bool`.
6. Define `RepositoryInfo(BaseModel)` with fields: `url`, `default_branch`, `commit_sha: str | None`, `clone_path`.
7. Define `ProjectMetadata(BaseModel)` with fields: `project_id`, `name`, `created_at`, `status` (`"pending"` | `"analyzing"` | `"ready"` | `"error"`), `error_message: str | None`.
8. Define top-level `ProjectKnowledge(BaseModel)` composing all of the above.
9. Write `tests/test_knowledge_models.py` with at least 3 tests: construction, JSON round-trip, optional field absence.

**Relevant Context**
- Use Pydantic v2 (`model_config`, `model_dump`, `model_validate`).
- `inferred: bool` on `Relationship` is the mechanism that satisfies the "detected facts vs inferred" design principle.
- `confidence: float` (0.0–1.0) satisfies the explainability principle.

---

### Sub-Task 3 — Filesystem Storage Layer

**Status:** `[ ] pending`

**Intent**
Provide a thin storage abstraction that reads and writes the Project Knowledge Model to disk. Defined behind a clean interface so it can be replaced by a database later without touching the analyzer or API.

**Expected Outcomes**
- `backend/app/knowledge/storage.py` exposes a `ProjectStorage` class.
- Public methods: `create_project`, `get_project`, `save_knowledge`, `load_knowledge`, `list_projects`, `get_clone_path`.
- The on-disk layout is exactly `projects/<project_id>/metadata.json` and `projects/<project_id>/knowledge.json`.
- `tests/test_storage.py` verifies save/load round-trip and list behaviour using a `tmp_path` pytest fixture (no real `projects/` directory used).

**Todo List**
1. Implement `ProjectStorage.__init__(self, base_path: Path)` — receives root storage path as dependency.
2. Implement `create_project(repo_url) -> ProjectMetadata` — generates a deterministic `project_id` (e.g. `slugify(repo_name) + short uuid`), writes `metadata.json`.
3. Implement `get_project(project_id) -> ProjectMetadata | None`.
4. Implement `save_knowledge(project_id, knowledge: ProjectKnowledge) -> None`.
5. Implement `load_knowledge(project_id) -> ProjectKnowledge | None`.
6. Implement `list_projects() -> list[ProjectMetadata]`.
7. Implement `get_clone_path(project_id) -> Path` — returns `projects/<id>/repository/`.
8. Write `tests/test_storage.py` using `tmp_path`.

**Relevant Context**
- `ProjectStorage` receives `base_path: Path` as a constructor argument. It is instantiated independently in both the FastAPI process and the MCP stdio process, each pointing at the same `projects/` directory on disk.
- The `projects/` directory is at the workspace root: `AtlasCode/projects/`.
- The storage interface must be clean enough that swapping the filesystem backend for a database only requires replacing this class.

---

### Sub-Task 4 — Repository Analyzer Pipeline

**Status:** `[ ] pending`

**Intent**
Implement the read-only analysis pipeline that transforms a cloned repository into a `ProjectKnowledge` object. Each stage is a separate module so new analyzers can be added independently.

**Expected Outcomes**
- `analyzer/repository.py` — clones/updates a Git repo into the storage path using GitPython.
- `analyzer/files.py` — walks the file tree and returns a list of `FileEntry`, tagging important manifest files.
- `analyzer/technologies.py` — detects technologies and versions by reading manifest files (no code execution).
- `analyzer/dependencies.py` — extracts direct dependencies from manifest files.
- `analyzer/relationships.py` — performs regex-based import detection for Python and TypeScript/JavaScript.
- A top-level `analyzer/pipeline.py` orchestrates all stages in order and returns `ProjectKnowledge`.
- Unit tests covering each stage using the fixture repository in `examples/fixtures/`.

**Todo List**
1. **`repository.py`**: implement `clone_repository(url, target_path)` using `git.Repo.clone_from`. Raises on failure. Never executes repository code.
2. **`files.py`**: implement `scan_files(repo_path) -> list[FileEntry]`. Walk with `os.walk`, skip `.git/`. Mark a file `is_important=True` if its name matches the known manifest list.
3. **`technologies.py`**: implement `detect_technologies(repo_path, file_entries) -> list[TechnologyDetection]`. Parse `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml` for language/framework names and versions. Also infer technology presence from file extensions (`.ts`, `.py`, `.go`, `.rs`, `.java`). Never guess versions.
4. **`dependencies.py`**: implement `extract_dependencies(repo_path, file_entries) -> list[Dependency]`. Parse the same manifests; return raw dependency name + version range + ecosystem.
5. **`relationships.py`**: implement `detect_relationships(repo_path, file_entries) -> list[Relationship]`. Use regex on `.py` files for `import X` / `from X import`. Use regex on `.ts`/`.js` files for `import ... from '...'`. Mark all results `inferred=True`, `confidence=0.6`.
6. **`pipeline.py`**: implement `run_pipeline(project_id, repo_url, storage) -> ProjectKnowledge`. Calls all stages in order; updates `metadata.status` to `"analyzing"` then `"ready"` (or `"error"`).
7. Create `examples/fixtures/sample-python-project/` with a minimal Python project: `pyproject.toml`, `requirements.txt`, two `.py` files with imports.
8. Create `examples/fixtures/sample-node-project/` with a minimal Node project: `package.json`, two `.ts` files with imports.
9. Write `tests/test_analyzer_files.py`, `tests/test_analyzer_technologies.py`, `tests/test_analyzer_dependencies.py`, `tests/test_analyzer_relationships.py` — all using fixture repos, no network calls.

**Relevant Context**
- GitPython is the preferred clone tool; fallback is `subprocess.run(["git", "clone", ...])`.
- The `is_important` flag on `FileEntry` drives which files the technology/dependency analyzers prioritize.
- `inferred=True` + lower confidence on relationships satisfies the "detected vs inferred" principle.

---

### Sub-Task 5 — FastAPI Backend & REST API

**Status:** `[ ] pending`

**Intent**
Wire the pipeline and storage into a FastAPI application that exposes the REST endpoints the frontend and other clients will call.

**Expected Outcomes**
- `app/main.py` creates the FastAPI app, mounts the router, configures CORS for the frontend dev server, and provides the `ProjectStorage` as a shared dependency.
- `app/api/projects.py` implements all required endpoints.
- Analysis runs as a background task so `POST /projects/analyze` returns immediately with `project_id` and `status: "analyzing"`.
- `tests/test_api.py` uses `httpx` + `TestClient` and the fixture repos to test all endpoints without network I/O.

**Todo List**
1. Implement `app/main.py`: create `FastAPI` instance, add `CORSMiddleware` (allow `http://localhost:5173`), include router from `app/api/projects`.
2. Implement `POST /projects/analyze`: accept `{"repository_url": "..."}`, create project record, enqueue `run_pipeline` as a `BackgroundTask`, return `{"project_id": "...", "status": "analyzing"}`.
3. Implement `GET /projects/{project_id}`: return `ProjectMetadata` + summary counts from `ProjectKnowledge`.
4. Implement `GET /projects/{project_id}/tree`: return `file_entries` from knowledge.
5. Implement `GET /projects/{project_id}/technologies`: return `technologies` from knowledge.
6. Implement `GET /projects/{project_id}/dependencies`: return `dependencies` from knowledge.
7. Implement `GET /projects/{project_id}/architecture`: return `components` + `relationships` from knowledge.
8. Add a `GET /projects/` list endpoint (bonus, needed by frontend).
9. Write `tests/test_api.py` using `TestClient`. Mock `clone_repository` so tests never hit the network. Use fixture repos for analysis tests.

**Relevant Context**
- `ProjectStorage` injected via `Depends(get_storage)` factory function in `main.py`.
- `BackgroundTasks` is the FastAPI built-in mechanism — no Celery or Redis needed for Phase 1.
- Return 404 with a clear message when `project_id` is not found.

---

### Sub-Task 6 — MCP Server

**Status:** `[ ] pending`

**Intent**
Expose the Project Knowledge Model to AI agents as MCP tools. The MCP server is a **separate process** from FastAPI, communicating via `stdio`. It independently instantiates `ProjectStorage` pointing at the shared `projects/` directory on disk. No analysis logic is duplicated.

**Expected Outcomes**
- `app/mcp/server.py` implements all six required MCP tools using the `mcp` Python SDK.
- The MCP server runs as a standalone `stdio` process: `python -m app.mcp.server`.
- It does NOT import FastAPI or share memory with the backend process.
- `search_code` is safe and bounded (see constraints below).
- `tests/test_mcp.py` verifies each tool returns the expected data shape using fixture knowledge written to a `tmp_path` storage.

**Todo List**
1. Add `mcp` Python SDK to `backend/requirements.txt` (`pip install mcp`).
2. Implement `app/mcp/server.py` as a standalone MCP server using `stdio` transport. On startup it instantiates `ProjectStorage(base_path=PROJECTS_DIR)` where `PROJECTS_DIR` is read from an environment variable (defaulting to `../projects` relative to the backend root).
3. Implement `get_project_overview(project_id: str)` — returns metadata + technology names + counts from `knowledge.json`.
4. Implement `get_repository_tree(project_id: str)` — returns the file tree from `knowledge.json`.
5. Implement `get_tech_stack(project_id: str)` — returns technologies with version and source from `knowledge.json`.
6. Implement `get_dependencies(project_id: str)` — returns the dependency list grouped by ecosystem from `knowledge.json`.
7. Implement `get_architecture(project_id: str)` — returns components and relationships from `knowledge.json`.
8. Implement `search_code(project_id: str, query: str)` with all of the following safety constraints:
   - Skip directories: `.git/`, `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`, `.tox/`.
   - Only read text files (skip binaries by catching `UnicodeDecodeError`).
   - Impose a hard limit: scan at most 500 files, return at most 50 matching lines.
   - Never execute any file; only `open()` + `read()`.
   - Return `[{"file": "...", "line": N, "text": "..."}]`.
9. Write `app/mcp/__main__.py` so `python -m app.mcp` starts the server.
10. Write `tests/test_mcp.py` verifying all six tools against fixture knowledge in a `tmp_path` storage. Mock `ProjectStorage` path so no real `projects/` directory is needed.

**Relevant Context**
- The `mcp` Python SDK exposes `@server.tool()` or `@mcp.tool()` decorator depending on version.
- MCP server and FastAPI share NO in-memory state. The filesystem `projects/` directory is the shared medium.
- `search_code` is the only tool that reads raw repository files; all others read only from `knowledge.json`.
- `PROJECTS_DIR` environment variable must be documented in `backend/.env.example`.

---

### Sub-Task 7 — React Frontend

**Status:** `[ ] pending`

**Intent**
Build a clean, developer-oriented UI that covers the full user journey: enter a URL → trigger analysis → view dashboard.

**Expected Outcomes**
- Landing page with URL input and Analyze button.
- Polling mechanism that checks `GET /projects/{id}` until `status === "ready"`.
- Dashboard with six navigation tabs: Overview, Architecture, Code Graph, Technologies, Dependencies, Repository.
- Architecture tab uses React Flow to render a graph of components and relationships.
- Repository tab shows an interactive collapsible file tree.
- Technologies tab shows cards with name, version, and evidence source.
- Dependencies tab shows a grouped list by ecosystem.
- No UI framework dependency beyond what Vite scaffold provides; plain CSS modules or inline styles are fine.

**Todo List**
1. Create `src/api/client.ts` — typed fetch wrappers for all backend endpoints.
2. Create `src/types/knowledge.ts` — TypeScript types mirroring the Pydantic models.
3. Create `src/pages/LandingPage.tsx` — URL input form, calls `POST /projects/analyze`, navigates to dashboard.
4. Create `src/pages/DashboardPage.tsx` — tab container, polls for analysis completion, routes to sub-views.
5. Create `src/components/OverviewPanel.tsx` — shows name, URL, language chips, framework chips, counts.
6. Create `src/components/TechnologiesPanel.tsx` — grid of technology cards with evidence badges.
7. Create `src/components/DependenciesPanel.tsx` — grouped list by ecosystem.
8. Create `src/components/RepositoryPanel.tsx` — recursive collapsible file tree component.
9. Create `src/components/ArchitectureGraph.tsx` — React Flow graph of components + relationships with zoom/pan/select.
10. Wire routing with `react-router-dom` (add as dependency): `/` → Landing, `/projects/:id` → Dashboard.
11. Style: use a dark developer theme (CSS variables), no heavy CSS framework.
12. Confirm `vite.config.ts` proxies `/projects` → `http://localhost:8000` to avoid CORS in dev.

**Relevant Context**
- React Flow package is `@xyflow/react` (v12+).
- Polling interval: 2 seconds, stop when `status === "ready"` or `"error"`.
- The frontend Dockerfile serves the Vite production build via `nginx`.

---

### Sub-Task 8 — Docker Compose & Local Run

**Status:** `[ ] pending`

**Intent**
Make the system runnable with a single command on any developer machine.

**Expected Outcomes**
- `docker-compose.yml` at workspace root starts `backend` and `frontend` containers.
- `docker compose up --build` brings both services up with no manual steps.
- Backend reachable at `http://localhost:8000`, frontend at `http://localhost:5173` (or `3000`).
- `README.md` documents exactly how to run locally, how to analyze a repo, and how to connect the MCP server to Bob.

**Todo List**
1. Write `backend/Dockerfile`: Python 3.12 slim, install deps from `requirements.txt`, run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2. Write `frontend/Dockerfile`: Node 20 alpine build stage → nginx serve static build.
3. Write `docker-compose.yml` at workspace root: two services (`backend`, `frontend`), volume-mount `./projects:/app/projects` into backend, expose `8000` and `5173`/`80`.
4. Add `backend/.env.example` documenting `PROJECTS_DIR=/app/projects` (Docker path) and `PROJECTS_DIR=../projects` (local dev path).
5. Write final `README.md` at workspace root covering all nine sections: vision, architecture, MCP process model, local run, analyze a repo, MCP tools, limitations, roadmap. No database, Redis, Celery, or auth steps in the run instructions.

**Relevant Context**
- `projects/` is at workspace root. Volume-mount keeps cloned repos persistent across container restarts.
- `projects/*/repository/` must be in `.gitignore`.
- No database, Redis, Celery, Neo4j, authentication, or LLM integration is added here or anywhere in Phase 1.

---

### Sub-Task 9 — Test Suite & Fixtures

**Status:** `[ ] pending`

**Intent**
Validate every layer of the system with tests that run entirely offline, using fixture repositories instead of live GitHub.

**Expected Outcomes**
- All tests pass with `pytest` from `backend/`.
- Tests cover: knowledge model, storage, each analyzer stage, API endpoints, MCP tools.
- No test makes a network call.
- `examples/fixtures/` contains at least two fixture repos (Python and Node).

**Todo List**
1. Verify fixtures created in Sub-Task 4 are complete enough for all test scenarios.
2. Add `conftest.py` with shared fixtures: `tmp_storage`, `sample_python_knowledge`, `sample_node_knowledge`.
3. Ensure `test_knowledge_models.py`, `test_storage.py`, `test_analyzer_*.py`, `test_api.py`, `test_mcp.py` all pass.
4. Add a `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]` section setting `testpaths = tests`.
5. Confirm no test imports or calls `clone_repository` with a real URL — mock it where needed.

**Relevant Context**
- Use `pytest-mock` or `unittest.mock.patch` to mock `git.Repo.clone_from`.
- `httpx.TestClient` wraps FastAPI for API tests without starting a server.

---

## Implementation Order

```
Sub-Task 1  →  Sub-Task 2  →  Sub-Task 3
                                    ↓
Sub-Task 4  ←──────────────────────┘
      ↓
Sub-Task 5  →  Sub-Task 6
      ↓
Sub-Task 7
      ↓
Sub-Task 8  →  Sub-Task 9
```

Each sub-task must be confirmed working before proceeding to the next.

---

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Storage | Filesystem JSON | No DB dependency in Phase 1; interface abstracted for future swap |
| Analysis trigger | FastAPI BackgroundTasks | No Celery/Redis needed; good enough for Phase 1 |
| MCP transport | stdio | Simplest; matches Bob's MCP client expectations |
| MCP process model | Separate process from FastAPI | Both independently read `projects/` via `ProjectStorage`; no shared memory |
| search_code safety | Blocked dirs + file cap + match cap | Never executes code; bounded so large repos don't hang |
| Relationship detection | Regex import scanning | AST parsing is over-engineered for Phase 1 |
| Frontend build | Vite + React TS | Fast dev loop; aligns with spec |
| Graph library | @xyflow/react | Specified in requirements |
| Clone tool | GitPython | Cleaner API than subprocess; easy to mock |

---

## Out of Scope (Phase 1)

- Issue analysis
- Code modification or generation
- Test execution
- AST-based deep analysis
- Authentication / multi-user
- PostgreSQL, Redis, Neo4j, Celery, Kubernetes
- LLM integration of any kind
- Execution of any repository code (`npm install`, `pip install`, `make`, `./scripts/*`, `docker build`, etc.)
- Nested `codeatlas/` directory — workspace root IS the project root
