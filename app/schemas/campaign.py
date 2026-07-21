"""Pydantic v2 schemas for campaign chat requests/responses and entity extraction."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message from a player or DM.

    Attributes:
        session_id: Identifier of the campaign session; used to select the
            LangGraph checkpoint thread.
        message: Raw user text to route into the agent graph.
    """

    session_id: uuid.UUID
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    """Non-streaming reply from the agent graph.

    Attributes:
        session_id: Echoed campaign session identifier.
        reply: Final assistant message content.
    """

    session_id: uuid.UUID
    reply: str


class ExtractedEntity(BaseModel):
    """A single world-state entity extracted from narrative text by the LLM.

    Used as a structured-output schema for LLM entity extraction calls, and
    as the shape persisted into the `entities` table's JSONB metadata column.

    Attributes:
        name: Canonical entity name (NPC, location, faction, item, quest).
        entity_type: Coarse category used for downstream filtering/UI grouping.
        summary: One or two sentence description as currently known to the party.
        attributes: Free-form structured metadata (e.g. hex coordinates, level
            range, faction alignment) stored as JSONB.
    """

    name: str
    entity_type: Literal["npc", "location", "faction", "item", "quest", "other"]
    summary: str
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
