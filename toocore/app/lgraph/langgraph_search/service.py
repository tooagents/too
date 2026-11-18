from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.lgraph.langgraph_search.graph import compiled_workflow
from app.lgraph.langgraph_search.state import StateSearch
from app.schemas.sch_ai import JWType
from app.schemas.sch_ai_router import RouterQueryRequest

StatusCallback = Callable[[str, dict], Awaitable[None] | None]


async def route_and_answer(
    payload: RouterQueryRequest,
    zjwt: JWType,
    db: AsyncSession,
    status_cb: StatusCallback | None = None,
) -> dict:
    initial_state: StateSearch = {
        "query": payload.query,
        "top_k": payload.top_k,
        "zjwt": zjwt,
        "db": db,
        "status_cb": status_cb,
    }
    result = await compiled_workflow.ainvoke(initial_state)
    return result.get("response") or {}
