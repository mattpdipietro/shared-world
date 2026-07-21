"""Discord OAuth2 login endpoints: redirect out, callback in, session cookie."""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.dependencies import get_current_person
from app.auth.discord import build_authorize_url, discord_avatar_url, fetch_discord_user
from app.auth.sessions import SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, create_session, delete_session
from app.db.models import Person
from app.db.session import get_db
from app.schemas.auth import PersonOut

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
OAUTH_STATE_COOKIE_NAME = "sw_oauth_state"
OAUTH_STATE_TTL_SECONDS = 60 * 5

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/discord/login",
    summary="Start Discord login",
    description="Redirects the browser to Discord's OAuth2 authorize page. "
    "Must be reached via full browser navigation, not fetch/XHR.",
)
async def discord_login() -> RedirectResponse:
    """Redirect to Discord's authorize page with a fresh CSRF `state`.

    Side effects:
        Sets a short-lived `sw_oauth_state` cookie mirroring the `state`
        query param sent to Discord, checked in `discord_callback`.
    """
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(build_authorize_url(state))
    response.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get(
    "/discord/callback",
    summary="Discord OAuth2 callback",
    description="Exchanges the authorization code for the Discord user, "
    "upserts the matching Person, establishes a session, and redirects back "
    "to the frontend.",
)
async def discord_callback(
    request: Request, code: str, state: str, db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    """Complete the OAuth2 round trip and log the user in.

    Args:
        code: Authorization code issued by Discord.
        state: CSRF token echoed back by Discord; must match the
            `sw_oauth_state` cookie set in `discord_login`.
        db: Injected async database session.

    Returns:
        A redirect to `FRONTEND_URL` with the session cookie set.

    Raises:
        HTTPException: 400 if `state` doesn't match the cookie (missing,
            expired, or forged callback).
    """
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if not expected_state or expected_state != state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OAuth state")

    discord_user = await fetch_discord_user(code)

    person = (
        await db.execute(select(Person).where(Person.discord_id == discord_user["id"]))
    ).scalar_one_or_none()
    if person is None:
        person = Person(
            discord_id=discord_user["id"],
            username=discord_user["username"],
            avatar_url=discord_avatar_url(discord_user),
        )
        db.add(person)
    else:
        person.username = discord_user["username"]
        person.avatar_url = discord_avatar_url(discord_user)
    await db.commit()

    session_id = await create_session(person.id)

    response = RedirectResponse(FRONTEND_URL)
    response.delete_cookie(OAUTH_STATE_COOKIE_NAME)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get(
    "/me",
    response_model=PersonOut,
    summary="Get the current logged-in person",
    description="Returns the person behind the request's session cookie, or 401 if not logged in.",
)
async def me(person: Person = Depends(get_current_person)) -> Person:
    """Return the authenticated person for the current session."""
    return person


@router.post(
    "/logout",
    summary="Log out",
    description="Invalidates the current session and clears the session cookie.",
)
async def logout(request: Request, response: Response) -> dict[str, str]:
    """Invalidate the current session, if any, and clear its cookie.

    Returns:
        `{"status": "ok"}` unconditionally — logging out with no active
        session is not an error.
    """
    response.delete_cookie(SESSION_COOKIE_NAME)
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is not None:
        await delete_session(session_id)
    return {"status": "ok"}
