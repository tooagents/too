"""
START -> Init -> DecideRoute --+-- rag     -> RAG ------+-- done  -> END
                  ^            |                       |
                  |            +-- sql     -> SQL -----+-- done  -> END
                  |            |                       |
                  |            +-- general -> General -------------> END
                  |                                    |
                  +------------- retry ----------------+
                    (from RAG, up to MAX_ATTEMPTS, SQL fallback RAG in node already)
"""
from langgraph.graph import END, START, StateGraph

from app.lgraph.langgraph_search.nodes import node_general,    node_init_state,    node_orchestration,    node_rag,    node_sql
from app.lgraph.langgraph_search.state import StateSearch

MAX_ATTEMPTS = 2

def route_after_rag(state: StateSearch) -> str:
    """Re-route only when RAG came back weak and attempts remain."""
    if state.get("answer_ok", True):return "done"
    if state.get("attempts", 0) >= MAX_ATTEMPTS:return "done"
    return "retry"


graph_ = StateGraph(StateSearch)
graph_.add_node("Init", node_init_state)
graph_.add_node("DecideRoute", node_orchestration)
graph_.add_node("RAG", node_rag)
graph_.add_node("SQL", node_sql)
graph_.add_node("General", node_general)

graph_.add_edge(START, "Init")
graph_.add_edge("Init", "DecideRoute")
graph_.add_conditional_edges(
    "DecideRoute",
    lambda state: state.get("route", "rag"),
    {"rag": "RAG", "sql": "SQL", "general": "General"},
)

# only RAG can loop back; SQL already falls back to RAG inside its node
graph_.add_conditional_edges("RAG", route_after_rag, {"done": END, "retry": "DecideRoute"})
graph_.add_edge("SQL", END)
graph_.add_edge("General", END)

compiled_workflow = graph_.compile()