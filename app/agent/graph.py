"""Core LangGraph state graph for the campaign agent.

Builds an uncompiled graph. Compilation (with a checkpointer) happens at the
API layer so the `AsyncSqliteSaver` context manager lifetime can be tied to
the FastAPI request/app lifespan, keeping the Uvicorn event loop unblocked.
"""

from __future__ import annotations

import os

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from ollama import AsyncClient

from app.agent.state import CampaignState
from app.agent.tools import lookup_lore

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

TOOLS = [lookup_lore]


async def assistant_node(state: CampaignState) -> dict:
    """Invoke the local Ollama model with the current conversation.

    Args:
        state: Current graph state. Reads `state["messages"]` as the
            conversation history to send to the model.

    Returns:
        A partial state update: `{"messages": [<model reply>]}`, merged into
        the running history by the `add_messages` reducer.

    Routes to:
        `tools` node (via `tools_condition`) if the model requests a tool
        call, otherwise `END`.
    """
    client = AsyncClient(host=OLLAMA_HOST)
    response = await client.chat(model=OLLAMA_MODEL, messages=state["messages"])
    return {"messages": [response["message"]]}


def build_graph() -> StateGraph:
    """Assemble the campaign agent's state graph.

    Returns:
        An uncompiled `StateGraph` wired as: `assistant` -> (`tools` | `END`),
        with `tools` looping back to `assistant`. Callers must `.compile()`
        this with a checkpointer before invoking it.
    """
    graph = StateGraph(CampaignState)
    graph.add_node("assistant", assistant_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    return graph
