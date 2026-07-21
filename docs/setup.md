---
title: Setup
description: Local setup guide — Poetry, Docker Compose infrastructure, database migrations, and running the API server.
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
- `redis` — exposed on `6379` (backs the login session store now, the
  Celery broker once background jobs land)
- `ollama` — exposed on `11434`

Pull the default model once the `ollama` container is up:

```bash
docker exec -it shared-world-ollama ollama pull llama3.1:8b
```

## 3. Initialize the database schema

```bash
poetry run alembic upgrade head
```

Runs all Alembic migrations, which enable the `vector` extension and create
every table declared in `app/db/models.py`. See
[Architecture → Migrations](architecture.md#migrations).

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
| `REDIS_URL` | `redis://localhost:6379/0` | Session store (and future Celery broker) |
| `DISCORD_CLIENT_ID` | *(empty)* | OAuth2 client id from the [Discord Developer Portal](https://discord.com/developers/applications) |
| `DISCORD_CLIENT_SECRET` | *(empty)* | OAuth2 client secret — keep out of version control |
| `DISCORD_REDIRECT_URI` | `http://localhost:8000/auth/discord/callback` | Must exactly match a redirect registered on the Discord application |
| `FRONTEND_URL` | `http://localhost:5173` | Where the OAuth callback redirects after login; also the allowed CORS origin |

`DISCORD_CLIENT_ID`/`DISCORD_CLIENT_SECRET` require creating a Discord
application: [Developer Portal](https://discord.com/developers/applications)
→ New Application → OAuth2 → add a redirect matching `DISCORD_REDIRECT_URI`
→ copy the client id/secret into a local `.env` (not committed).
