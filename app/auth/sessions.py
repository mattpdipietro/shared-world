"""Server-side session store, backed by Redis.

Sessions are opaque tokens mapping to a `Person.id`, stored in Redis with a
TTL. The browser only ever holds the opaque `session_id` in an HttpOnly
cookie — no JWT, no client-readable session state. This reuses the Redis
instance the project already runs for Celery (see docs/roadmap.md), rather
than adding a second session-store technology.
"""

from __future__ import annotations

import os
import secrets
import uuid

from redis.asyncio import Redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SESSION_COOKIE_NAME = "sw_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14  # 14 days

_redis = Redis.from_url(REDIS_URL, decode_responses=True)


def _key(session_id: str) -> str:
    return f"session:{session_id}"


async def create_session(person_id: uuid.UUID) -> str:
    """Create a new session for a person and return its opaque id.

    Args:
        person_id: The `Person.id` this session authenticates as.

    Returns:
        A URL-safe session id to set as the `sw_session` cookie value.
    """
    session_id = secrets.token_urlsafe(32)
    await _redis.set(_key(session_id), str(person_id), ex=SESSION_TTL_SECONDS)
    return session_id


async def get_session_person_id(session_id: str) -> uuid.UUID | None:
    """Resolve a session id to the person it belongs to.

    Args:
        session_id: The value read from the `sw_session` cookie.

    Returns:
        The `Person.id` the session authenticates as, or `None` if the
        session id is missing, unknown, or expired.
    """
    raw = await _redis.get(_key(session_id))
    return uuid.UUID(raw) if raw else None


async def delete_session(session_id: str) -> None:
    """Invalidate a session immediately (used by logout).

    Args:
        session_id: The value read from the `sw_session` cookie.
    """
    await _redis.delete(_key(session_id))
