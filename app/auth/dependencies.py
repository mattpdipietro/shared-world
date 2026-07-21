"""FastAPI dependencies for reading the authenticated person off a request."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import SESSION_COOKIE_NAME, get_session_person_id
from app.db.models import Person
from app.db.session import get_db


async def get_current_person(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Person:
    """Resolve the `Person` behind the request's session cookie.

    Args:
        request: Used to read the `sw_session` cookie.
        db: Injected async database session.

    Returns:
        The `Person` row the session belongs to.

    Raises:
        HTTPException: 401 if there's no session cookie, the session is
            unknown/expired, or (unexpectedly) its person no longer exists.
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")

    person_id = await get_session_person_id(session_id)
    if person_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    person = await db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")

    return person
