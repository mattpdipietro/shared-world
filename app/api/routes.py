"""FastAPI routers for the campaign agent API."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.campaign import ChatRequest, ChatResponse

router = APIRouter()


@router.get("/health", summary="Liveness check", description="Returns 200 if the API process is up.")
async def health() -> dict[str, str]:
    """Liveness probe.

    Returns:
        A static `{"status": "ok"}` payload. Does not check downstream
        Postgres/Ollama availability — see `/health/ready` once added.
    """
    return {"status": "ok"}


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the campaign agent",
    description="Invokes the compiled LangGraph agent for the given session "
    "and returns the final assistant reply. Non-streaming; use the SSE "
    "endpoint (once added) for token-by-token output.",
)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """Route a chat message through the compiled campaign agent graph.

    Args:
        payload: Session id and user message.
        request: Used to reach the compiled graph stored on `app.state.graph`
            (compiled once at startup with the shared checkpointer).

    Returns:
        The final assistant message for this turn.

    Side effects:
        Persists the updated conversation state via the graph's
        `AsyncSqliteSaver` checkpointer, keyed by `payload.session_id`.
    """
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": str(payload.session_id)}}
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": payload.message}], "session_id": str(payload.session_id)},
        config=config,
    )
    reply = result["messages"][-1]["content"]
    return ChatResponse(session_id=payload.session_id, reply=reply)
