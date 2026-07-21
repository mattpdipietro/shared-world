"""LangGraph state schema for the campaign agent.

Zero FastAPI dependencies — this module is imported only by other `app/agent`
modules and by API-layer callers that invoke the compiled graph.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class CampaignState(TypedDict):
    """Shared state threaded through every node in the campaign agent graph.

    Attributes:
        messages: Full conversation history. Uses the `add_messages` reducer
            so concurrent/parallel node writes append rather than overwrite
            the list.
        session_id: Campaign session identifier, used to scope world-state
            lookups and RAG retrieval to the correct partner/campaign.
    """

    messages: Annotated[list, add_messages]
    session_id: str
