"""One-shot async DDL bootstrap for the campaign world-state database.

Enables the `pgvector` extension and creates all tables declared on
`app.db.models.Base`. Intended for local/dev use; swap for Alembic
migrations before this schema needs versioned, reversible changes.
"""

from __future__ import annotations

from sqlalchemy import text

from app.db.models import Base
from app.db.session import engine


async def init_db() -> None:
    """Enable required Postgres extensions and create all declared tables."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
