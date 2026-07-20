# CLAUDE.md — Local AI D&D Campaign Engine

## Project Context
Building a local, containerized AI campaign management co-pilot for D&D (West Marches style). 
Core goals: Long-term world state tracking, entity extraction, state persistence, and RAG over campaign lore.

---

## Technical Stack Requirements
* **Language/Runtime:** Python 3.11+
* **Dependency & Environment Management:** Poetry
* **Documentation & Site Generator:** MkDocs with `mkdocs-material` (deployed to GitHub Pages)
* **Orchestration:** LangGraph (StateGraph, tool routing, memory)
* **API Framework:** FastAPI (async routes, WebSockets/SSE streaming)
* **State Checkpointing:** `AsyncSqliteSaver` via `aiosqlite`
* **Database / Vector:** PostgreSQL + `pgvector` (via Docker Compose)
* **Local Inference:** Ollama API (`llama3.1:8b` default)
* **Containerization:** Docker & Docker Compose

---

## Architectural Rules & Code Boundaries

1. **Decoupled Architecture:** 
   * `/app/agent/`: Core LangGraph graph definitions, nodes, tools, and schemas. Zero FastAPI dependencies here.
   * `/app/api/`: FastAPI routers, dependency injection, and middleware.
   * `/app/db/`: Async SQLAlchemy / asyncpg database connection handlers and DDL migrations.
   * `/app/schemas/`: Pydantic v2 schemas for request/response payloads and LLM structured outputs.

2. **LangGraph State Management:**
   * Always explicitly type the `StateGraph` schema using `TypedDict` or `Pydantic`.
   * Use `Annotated[list, add_messages]` for message state reducers to prevent key overwrite.
   * All state checkpointing must use `AsyncSqliteSaver` inside FastAPI handlers to keep the Uvicorn event loop unblocked.

3. **Database & Data Schema Conventions:**
   * Primary key fields MUST use `UUID` (`gen_random_uuid()`).
   * Vector embeddings MUST be 768-dimension (`vector(768)`) to align with `nomic-embed-text` / standard local embeddings.
   * Use JSONB for flexible entity metadata (e.g., hex coordinates, level ranges).

4. **Async-First Execution:**
   * All database calls, file I/O, and LLM invocation hooks MUST be non-blocking (`async`/`await`).

---

## Documentation & Docstring Standards

* **Docstring Style:** Use **Google-style docstrings** for all modules, classes, and public functions/nodes.
* **LangGraph Nodes & Tools:** 
  * Every node function must have a clear docstring explaining its input state expectations, state transitions, and downstream router targets.
  * Custom tools MUST include detailed descriptions in their docstrings; the LLM uses these descriptions directly for tool-calling decisions.
* **FastAPI Routes:** Include a concise summary and description in route decorators, plus inline docstrings explaining expected response models and side-effects.
* **Project Documentation (GitHub Pages):**
  * All user guides, architecture diagrams, and setup instructions live under `/docs/` in Markdown (`.md`).
  * Add `mkdocs-material` as a dev dependency in Poetry (`poetry add --group dev mkdocs-material`).
  * Maintain `mkdocs.yml` at the repository root to configure navigation, theme, and site metadata.
  * When adding major system features or node graphs, update the corresponding file in `/docs/` prior to pushing code.

---

## Project Directory Structure Target
```text
.
├── app/
│   ├── agent/             # LangGraph state graph, nodes, and tool definitions
│   ├── api/               # FastAPI route handlers and endpoints
│   ├── db/                # Postgres/pgvector connections & SQLite checkpointer setup
│   ├── schemas/           # Pydantic models (API inputs/outputs & LLM extraction schemas)
│   └── main.py            # FastAPI entry point
├── docs/                  # GitHub Pages documentation source files
│   ├── index.md           # Documentation homepage
│   ├── architecture.md    # Graph topology & database design specs
│   └── setup.md           # Local setup guide
├── tests/                 # Pytest suite
├── docker-compose.yml     # Local services (Postgres + pgvector)
├── mkdocs.yml             # MkDocs configuration file for GitHub Pages
├── pyproject.toml         # Poetry package config and dependency tree
├── poetry.lock            # Lockfile for reproducible builds
└── README.md

---

## Setup & Execution Commands
- **Initialize & Install Dependencies:** `poetry install`
- **Add New Dependency:** `poetry add <package-name>` (use `--group dev` for dev/doc tooling)
- **Spawn Shell Environment:** `poetry shell`
- **Spin Up Infrastructure:** `docker-compose up -d`
- **Run API Server:** `poetry run uvicorn app.main:app --reload --port 8000`
- **Run Test Suite:** `poetry run pytest -v`
- **Serve Docs Locally:** `poetry run mkdocs serve -a localhost:8001` (previews on http://127.0.0.1:8001)
- **Deploy Docs to GitHub Pages:** `poetry run mkdocs gh-deploy`

## Code Quality & Style
- Use Pydantic v2 for validation schemas.
- Include explicit Python type hints on all function signatures.
- Keep node functions pure and deterministic where possible; place side effects inside isolated tool calls.
