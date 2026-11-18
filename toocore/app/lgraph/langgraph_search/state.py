# app/lgraph/langgraph_search/state.py
from typing import Any, TypedDict


class StateSearch(TypedDict, total=False):
    # ---- inputs (plain data only: everything here is checkpointed) ----
    query: str
    top_k: int

    # ---- routing ----
    route: str
    decision: dict[str, Any]
    route_reasoning: list[str]
    tried_routes: list[str]
    attempts: int

    # ---- RAG ----
    rag_response: dict[str, Any]
    answer_ok: bool

    # ---- SQL ----
    sql_text: str
    sql_rationale: str | None
    sql_reasoning: list[str]

    # ---- general ----
    general_payload: dict[str, Any]
    general_reasoning: list[str]

    # ---- approval (new) ----
    sql_risks: list[str]      # empty = safe, skip the gate
    approval_id: str          # key into the approvals table
    approval_status: str      # "pending" | "approved" | "rejected" | "expired"

    # ---- output ----
    response: dict[str, Any]


# Runtime dependencies. NOT in state: pass via config on every invoke AND every resume.
#   config = {"configurable": {
#       "thread_id": "...",
#       "db": session,            # AsyncSession
#       "status_cb": callback,
#       "zjwt": jwt,
#   }}
# Nodes read them with:  config["configurable"]["db"]



# from collections.abc import Awaitable, Callable
# from typing import Any, TypedDict

# from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sch_ai import JWType


# class StateSearch(TypedDict, total=False):
#     query: str
#     top_k: int
#     zjwt: JWType
#     db: AsyncSession
#     status_cb: Callable[[str, dict[str, Any]], Awaitable[None] | None]
#     route: str
#     decision: dict[str, Any]
#     route_reasoning: list[str]
#     rag_response: dict[str, Any]
#     sql_text: str
#     sql_rationale: str | None
#     sql_reasoning: list[str]
#     general_payload: dict[str, Any]
#     general_reasoning: list[str]
#     response: dict[str, Any]
#     attempts: int
#     answer_ok: bool
#     tried_routes: list[str]
