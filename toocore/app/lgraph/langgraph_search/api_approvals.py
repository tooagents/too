# app/lgraph/langgraph_search/api_approvals.py
import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from toocore.app.lgraph.core_tools import validate_sql_select
from app.lgraph.langgraph_search.hitl_approvals import decide, get_approval, list_pending
from app.schemas.sch_ai import JWType

# GUESS: replace with your project's real dependencies
from app.deps import get_db, get_jwt   # get_db -> AsyncSession, get_jwt -> JWType

log = logging.getLogger(__name__)
router = APIRouter(prefix="/approvals", tags=["approvals"])

# Who may approve which kind. Adapt to however roles live in your JWT.
APPROVER_ROLES: dict[str, set[str]] = {
    "sql_query": {"admin", "data_approver"},
}


class DecisionIn(BaseModel):
    action: Literal["approve", "reject", "edit"]
    sql: str | None = None        # required when action == "edit"
    comment: str | None = None


def get_graph(request: Request):
    return request.app.state.graph


def _check_can_approve(jwt: JWType, kind: str, requester_id: uuid.UUID | None) -> None:
    role = (jwt.app_metadata or {}).get("role")
    if role not in APPROVER_ROLES.get(kind, set()):
        raise HTTPException(403, "You are not allowed to approve this kind of request")
    if requester_id is not None and jwt.zuid == requester_id:
        raise HTTPException(403, "You cannot approve your own request")


@router.get("/pending")
async def pending(db: AsyncSession = Depends(get_db), jwt: JWType = Depends(get_jwt)):
    rows = await list_pending(db, jwt.ztid)
    return [
        {
            "id": str(r.id),
            "kind": r.kind,
            "payload": r.payload,
            "requester_email": r.requester_email,
            "created_at": r.created_at,
            "expires_at": r.expires_at,
        }
        for r in rows
    ]


@router.post("/{approval_id}/decision")
async def submit_decision(
    approval_id: uuid.UUID,
    body: DecisionIn,
    db: AsyncSession = Depends(get_db),
    jwt: JWType = Depends(get_jwt),
    graph=Depends(get_graph),
) -> dict[str, Any]:
    # 1. load (tenant-scoped) and authorize
    row = await get_approval(db, approval_id, jwt.ztid)
    if row is None:
        raise HTTPException(404, "Approval not found")
    _check_can_approve(jwt, row.kind, row.usr_id)

    # 2. validate an edit BEFORE we burn the one-time transition
    resume: dict[str, Any] = {"action": body.action}
    if body.action == "edit":
        if not body.sql:
            raise HTTPException(422, "sql is required for action=edit")
        ok, reason = validate_sql_select(body.sql)
        if not ok:
            raise HTTPException(422, f"Edited SQL rejected: {reason}")
        resume["sql"] = body.sql

    # 3. atomic pending -> decided. Exactly one caller wins.
    new_status = "rejected" if body.action == "reject" else "approved"
    won = await decide(
        db,
        approval_id=approval_id,
        tenant_id=jwt.ztid,
        approver_id=jwt.zuid,
        new_status=new_status,
        decision={**resume, "comment": body.comment},
    )
    if not won:
        raise HTTPException(409, "Already decided or expired")

    # 4. resume as the REQUESTER, not the approver, so the query runs with the
    #    requester's data access. We rebuild the identity from stored ids.
    requester_jwt = JWType(
        zuid=row.usr_id,
        ztid=row.ten_id,
        zbid=row.biz_id,
        zcid=row.cli_id,
        zemail=row.requester_email,
    )
    config = {"configurable": {"thread_id": row.thread_id, "db": db, "zjwt": requester_jwt}}

    try:
        result = await graph.ainvoke(Command(resume=resume), config)
    except Exception:
        log.exception("resume failed approval_id=%s thread_id=%s", approval_id, row.thread_id)
        raise HTTPException(500, "Decision saved but the run failed to resume")

    # TODO notification stub: tell requester_email the outcome
    return {"approval_id": str(approval_id), "status": new_status, "response": result.get("response")}