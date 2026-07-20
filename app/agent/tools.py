"""Tool definitions available to the campaign agent.

Each tool's docstring is used directly by the LLM to decide when and how to
call it, so descriptions must be precise and example-driven rather than
implementation notes for other developers.
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
async def lookup_lore(query: str) -> str:
    """Search the campaign's world lore and past session notes for a topic.

    Call this whenever the player references an NPC, location, faction, item,
    or past event that isn't already present in the conversation, before
    inventing new details. Do not call this for purely mechanical questions
    (e.g. dice rules) — only for world/lore facts.

    Args:
        query: A short natural-language description of what to look up, e.g.
            "the mayor of Port Callow" or "what happened at the siege of
            Greywatch".

    Returns:
        The most relevant lore passages found, or a message indicating no
        matching lore exists yet (in which case the DM/agent should treat the
        topic as new canon and record it).
    """
    # Placeholder: RAG retrieval over pgvector wired in once the vector
    # store and embedding pipeline (nomic-embed-text via Ollama) are in place.
    raise NotImplementedError("RAG retrieval not yet implemented")
