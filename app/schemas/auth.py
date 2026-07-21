"""Pydantic v2 schemas for the authenticated-person API surface."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class PersonOut(BaseModel):
    """The current session's authenticated person, as returned by `/auth/me`.

    Attributes:
        id: Primary key of the `people` row.
        discord_id: Durable Discord user id backing this identity.
        username: Discord display name at last login.
        avatar_url: Discord CDN avatar URL, or `None` if the user has no
            custom avatar set.
    """

    id: uuid.UUID
    discord_id: str
    username: str
    avatar_url: str | None

    model_config = {"from_attributes": True}
