from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sch_ai import JWType


class StateSearch(TypedDict, total=False):
    query: str
    top_k: int
    zjwt: JWType
    db: AsyncSession
    status_cb: Callable[[str, dict[str, Any]], Awaitable[None] | None]
    route: str
    decision: dict[str, Any]
    route_reasoning: list[str]
    rag_response: dict[str, Any]
    sql_text: str
    sql_rationale: str | None
    sql_reasoning: list[str]
    general_payload: dict[str, Any]
    general_reasoning: list[str]
    response: dict[str, Any]
    attempts: int
    answer_ok: bool
    tried_routes: list[str]
