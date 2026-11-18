# app/lgraph/langgraph_search/graph.py
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from app.lgraph.langgraph_search.nodes import (
    node_general,
    node_init_state,
    node_orchestration,
    node_rag,
)
from app.lgraph.langgraph_search.nodes_approval import (
    node_approval_gate,
    node_request_approval,
    node_sql_execute,
    node_sql_fallback,
    node_sql_generate,
    node_sql_giveup,
    route_after_execute,
    route_after_generate,
)
from app.lgraph.langgraph_search.state import StateSearch

MAX_ATTEMPTS = 2


def route_after_rag(state: StateSearch) -> str:
    """Re-route only when RAG came back weak and attempts remain."""
    if state.get("answer_ok", True):
        return "done"
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "done"
    return "retry"


def build_graph(checkpointer: BaseCheckpointSaver):
    g = StateGraph(StateSearch)

    g.add_node("Init", node_init_state)
    g.add_node("DecideRoute", node_orchestration)
    g.add_node("RAG", node_rag)
    g.add_node("General", node_general)

    # SQL branch: the old single "SQL" node is now four nodes
    g.add_node("SQLGenerate", node_sql_generate)
    g.add_node("RequestApproval", node_request_approval)
    g.add_node("SQLFallback", node_sql_fallback)
    g.add_node("SQLGiveUp", node_sql_giveup)
    g.add_node("ApprovalGate", node_approval_gate)
    g.add_node("SQLExecute", node_sql_execute)

    g.add_conditional_edges(
        "SQLGenerate", route_after_generate,
        ["SQLFallback", "SQLGiveUp", "RequestApproval", "SQLExecute"],
    )
    g.add_edge("RequestApproval", "ApprovalGate")
    # no edge out of ApprovalGate: it returns Command(goto=...) itself
    g.add_conditional_edges(
        "SQLExecute", route_after_execute,
        ["SQLGenerate", "SQLFallback", "SQLGiveUp", END],
    )
    g.add_edge("SQLFallback", END)
    g.add_edge("SQLGiveUp", END)
    
    g.add_edge(START, "Init")
    g.add_edge("Init", "DecideRoute")
    g.add_conditional_edges(
        "DecideRoute",
        lambda state: state.get("route", "rag"),
        {"rag": "RAG", "sql": "SQLGenerate", "general": "General"},
    )

    g.add_conditional_edges("RAG", route_after_rag, {"done": END, "retry": "DecideRoute"})

    g.add_conditional_edges(
        "SQLGenerate", route_after_generate, ["RAG", "RequestApproval", "SQLExecute"]
    )
    g.add_edge("RequestApproval", "ApprovalGate")
    # no edge out of ApprovalGate: it returns Command(goto=...) itself
    g.add_edge("SQLExecute", END)
    g.add_edge("General", END)

    return g.compile(checkpointer=checkpointer)


@asynccontextmanager
async def open_graph(pg_url: str):
    """Persistent graph. Call once at app startup (FastAPI lifespan)."""
    async with AsyncPostgresSaver.from_conn_string(pg_url) as saver:
        await saver.setup()      # creates checkpoint tables if missing
        yield build_graph(saver)