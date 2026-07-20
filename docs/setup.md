---
title: Setup
description: Local setup guide — Poetry, Docker Compose infrastructure, database bootstrap, and running the API server.
---

# Local Setup

## Prerequisites

- Python 3.12+ (this repo pins `python = "^3.12"` in `pyproject.toml`)
- [Poetry](https://python-poetry.org/)
- Docker + Docker Compose (Postgres/pgvector and Ollama both run as containers)

## 1. Install dependencies

```bash
poetry install
```

## 2. Start infrastructure

```bash
docker-compose up -d
```

This starts:

- `postgres` — `pgvector/pgvector:pg16`, exposed on `5432`
- `ollama` — exposed on `11434`

Pull the default model once the `ollama` container is up:

```bash
docker exec -it shared-world-ollama ollama pull llama3.1:8b
```

## 3. Initialize the database schema

```bash
poetry run python -c "import asyncio; from app.db.bootstrap import init_db; asyncio.run(init_db())"
```

This enables the `vector` extension and creates all tables declared in
`app/db/models.py`.

## 4. Run the API server

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

- Health check: `GET http://localhost:8000/health`
- Chat: `POST http://localhost:8000/chat` with `{"session_id": "<uuid>", "message": "..."}`

## 5. Run tests

```bash
poetry run pytest -v
```

## 6. Docs site (this site)

```bash
poetry run mkdocs serve -a localhost:8001
```

Preview at <http://127.0.0.1:8001>. Deploy with `poetry run mkdocs gh-deploy`.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://shared_world:shared_world@localhost:5432/shared_world` | Postgres connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Default chat model |
