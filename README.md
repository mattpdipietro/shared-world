# shared-world

Local, containerized AI campaign management co-pilot for D&D (West Marches
style) — long-term world state tracking, entity extraction, and RAG over
campaign lore.

Full docs: [`docs/index.md`](docs/index.md) (or `poetry run mkdocs serve -a localhost:8001`).

## Quickstart

```bash
poetry install
docker-compose up -d
docker exec -it shared-world-ollama ollama pull llama3.1:8b
poetry run python -c "import asyncio; from app.db.bootstrap import init_db; asyncio.run(init_db())"
poetry run uvicorn app.main:app --reload --port 8000
```

See [`docs/setup.md`](docs/setup.md) for details, [`docs/architecture.md`](docs/architecture.md)
for the technical design, [`docs/data-model.md`](docs/data-model.md) for the
entity design, and [`docs/roadmap.md`](docs/roadmap.md) for the phased plan
for upcoming features.
