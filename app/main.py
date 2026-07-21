"""FastAPI application entry point.

Wires the LangGraph campaign agent to an `AsyncSqliteSaver` checkpointer for
the lifetime of the app, and exposes the API routers.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import build_graph
from app.api.routes import router
from app.auth.router import router as auth_router

CHECKPOINT_DB_PATH = "checkpoints.sqlite"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(auth_router)
