"""Async SQLAlchemy engine and session factory for the Postgres/pgvector store."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://shared_world:shared_world@localhost:5432/shared_world",
)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async database session.

    Yields:
        An `AsyncSession` bound to the module-level engine. The session is
        closed automatically when the request completes.
    """
    async with async_session_factory() as session:
        yield session
