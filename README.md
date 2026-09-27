# CodeAtlas

> **Map any codebase. Understand any issue.**

CodeAtlas is an MCP-powered codebase intelligence platform. Point it at any public GitHub repository and get a structured knowledge model — technologies, dependencies, architecture, and file tree — surfaced in a React dashboard and exposed as MCP tools that AI coding agents can consume directly.

---

## Table of Contents

1. [Vision](#vision)
2. [Architecture](#architecture)
3. [MCP Process Model](#mcp-process-model)
4. [Local Run](#local-run)
5. [Analyze a Repository](#analyze-a-repository)
6. [MCP Tools](#mcp-tools)
7. [REST API](#rest-api)
8. [Limitations (Phase 1)](#limitations-phase-1)
9. [Roadmap](#roadmap)

---

## Vision

Developers spending time on an unfamiliar codebase — whether debugging a production issue or onboarding to a new project — waste hours just building a mental model of what exists and how it fits together. CodeAtlas automates that first step: it reads the repository, extracts traceable facts, and makes them available both to humans (via the dashboard) and to AI agents (via MCP tools).

**Core principles:**
- Every detected fact has a traceable evidence source (`source` field) and a confidence score.
- Nothing is executed from the repository. Analysis is 100% read-only.
- The filesystem is the single source of truth. FastAPI and the MCP server are independent processes that both read from `projects/`.

---

## Architecture

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

**On-disk layout per project:**
```
projects/
└── <project_id>/
    ├── metadata.json     # status, name, created_at, error_message
    ├── knowledge.json    # full ProjectKnowledge object
    └── repository/       # git clone (never committed — .gitignore'd)
```

---

## MCP Process Model

The MCP server is a **separate OS process** from the FastAPI backend. They share **no in-memory state**.

```
FastAPI process   ──writes──►  projects/<id>/knowledge.json  ◄──reads──  MCP stdio process
```

This means:
- You can restart the MCP server without touching the API.
- The MCP server can be connected to Bob (or any MCP client) while the backend is not running, as long as `knowledge.json` files already exist on disk.
- `PROJECTS_DIR` must point to the same directory in both processes.

---

## Local Run

### Prerequisites

- Docker + Docker Compose v2  **or** Python 3.12 + Node 20 for the manual path

### Docker (recommended)

```bash
git clone https://github.com/your-org/codeatlas
cd codeatlas
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |

The `projects/` directory is volume-mounted so cloned repos and knowledge files persist across restarts.

### Manual (no Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PROJECTS_DIR=../projects uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/projects` and `/health` to `http://localhost:8000` automatically.

---

## Analyze a Repository

### Via the UI

1. Open http://localhost:3000 (Docker) or http://localhost:5173 (dev)
2. Paste a public GitHub URL, e.g. `https://github.com/pallets/flask`
3. Click **Analyze** — the dashboard opens immediately and polls until analysis completes
4. Explore the **Overview**, **Technologies**, **Dependencies**, **Architecture**, and **Repository** tabs

### Via the API

```bash
# Start analysis
curl -s -X POST http://localhost:8000/projects/analyze \
  -H 'Content-Type: application/json' \
  -d '{"repository_url": "https://github.com/pallets/flask"}' | jq .

# Poll until ready
curl -s http://localhost:8000/projects/<project_id> | jq .status
```

---

## MCP Tools

Start the MCP server as a stdio process (run from `backend/`):

```bash
PROJECTS_DIR=../projects python -m app.mcp
```

### Connecting to Bob

Add this to your Bob MCP config:

```json
{
  "mcpServers": {
    "codeatlas": {
      "command": "python",
      "args": ["-m", "app.mcp"],
      "cwd": "/path/to/AtlasCode/backend",
      "env": {
        "PROJECTS_DIR": "/path/to/AtlasCode/projects"
      }
    }
  }
}
```

### Available tools

| Tool | Description |
|------|-------------|
| `get_project_overview` | Metadata, technology names, and summary counts |
| `get_repository_tree` | Full file list with sizes and importance flags |
| `get_tech_stack` | Detected technologies with version, source, and confidence |
| `get_dependencies` | All dependencies grouped by ecosystem (npm, pypi, …) |
| `get_architecture` | Components and import relationships |
| `search_code` | Case-insensitive text search across repository files (bounded: max 500 files, 50 matches) |

All tools accept `project_id: str` as their first argument. Use `get_project_overview` first to discover the correct ID.

---

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/projects/analyze` | Start analysis of a GitHub repo |
| `GET` | `/projects/` | List all projects |
| `GET` | `/projects/{id}` | Project summary + status |
| `GET` | `/projects/{id}/tree` | File tree |
| `GET` | `/projects/{id}/technologies` | Technology detections |
| `GET` | `/projects/{id}/dependencies` | Dependency list |
| `GET` | `/projects/{id}/architecture` | Components + relationships |
| `GET` | `/health` | Health check |

Full interactive docs: http://localhost:8000/docs

---

## Limitations (Phase 1)

- **Public repositories only** — no auth, no private repo support
- **No issue analysis** — CodeAtlas maps structure, not history
- **Regex-based relationship detection** — import scanning only; no full AST analysis
- **Read-only** — no code modification, generation, or execution of any kind
- **Single machine** — no distributed storage, no Redis, no database
- **No authentication** — single-user local tool only
- **Analysis is sequential** — one background task at a time per process; concurrent analyses may conflict on large repos

---

## Roadmap

**Phase 2 (Current)**
- **Guided Contribution Mode**: Act as an interactive mentor to guide developers through fixing issues, telling them where to write code and tests, running tests on demand, and preparing a Pull Request summary.
- PostgreSQL storage backend (drop-in swap via `ProjectStorage` interface)
- Private repository support via GitHub App OAuth
- AST-based relationship detection for Python and TypeScript
- Issue ↔ code linking: given a GitHub issue number, surface the relevant files and components

**Phase 3 (ideas)**
- Multi-repo workspace — compare dependencies across a fleet of services
- Incremental re-analysis on push events (GitHub webhook)
- LLM-assisted summarization as an optional layer on top of the knowledge model
