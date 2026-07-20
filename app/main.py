"""FastAPI application entry point.

Wires the LangGraph campaign agent to an `AsyncSqliteSaver` checkpointer for
the lifetime of the app, and exposes the API routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import build_graph
from app.api.routes import router

CHECKPOINT_DB_PATH = "checkpoints.sqlite"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Compile the campaign agent graph with an async SQLite checkpointer.

    The `AsyncSqliteSaver` context manager is kept open for the app's entire
    lifetime so the same non-blocking connection backs every request;
    compiling per-request would reopen/close the SQLite file on every call.
    """
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as checkpointer:
        app.state.graph = build_graph().compile(checkpointer=checkpointer)
        yield


app = FastAPI(
    title="Shared World — Campaign Engine",
    description="Local AI co-pilot for long-term D&D world-state tracking, "
    "entity extraction, and RAG over campaign lore.",
    lifespan=lifespan,
)
app.include_router(router)
