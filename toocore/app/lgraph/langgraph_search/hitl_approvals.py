# app/lgraph/langgraph_search/hitl_approvals.py
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, String, Uuid, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.too.z_base import Base, BaseMixin
from app.schemas.sch_ai import JWType


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Approval(Base, BaseMixin):
    __tablename__ = "approvals"

    requester_email: Mapped[str | None] = mapped_column(String)
    thread_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)                 # "sql_query", "refund", ...
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # status (from mixin): pending | approved | rejected | expired


async def create_approval(
    db: AsyncSession,
    *,
    jwt: JWType,
    thread_id: str,
    kind: str,
    payload: dict[str, Any],
    ttl_days: int = 7,
) -> Approval:
    row = Approval(
        ten_id=jwt.ztid,
        biz_id=jwt.zbid,
        cli_id=jwt.zcid,
        usr_id=jwt.zuid,              # requester
        created_by=jwt.zuid,
        requester_email=jwt.zemail,
        thread_id=thread_id,
        kind=kind,
        payload=payload,
        status="pending",             # explicit: the mixin's python default is "active"
        expires_at=_now() + timedelta(days=ttl_days),
    )
    db.add(row)
    await db.commit()                 # must be durable BEFORE the graph pauses
    await db.refresh(row)
    return row


async def get_approval(
    db: AsyncSession, approval_id: uuid.UUID, tenant_id: uuid.UUID | None
) -> Approval | None:
    q = select(Approval).where(Approval.id == approval_id, Approval.ten_id == tenant_id)
    return (await db.execute(q)).scalar_one_or_none()


async def list_pending(db: AsyncSession, tenant_id: uuid.UUID | None) -> list[Approval]:
    q = (
        select(Approval)
        .where(Approval.ten_id == tenant_id, Approval.status == "pending")
        .order_by(Approval.created_at)
    )
    return list((await db.execute(q)).scalars())


async def decide(
    db: AsyncSession,
    *,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
    approver_id: uuid.UUID | None,
    new_status: str,                       # "approved" | "rejected"
    decision: dict[str, Any],
) -> bool:
    """One-time transition pending -> approved/rejected. False if already decided or expired."""
    result = await db.execute(
        update(Approval)
        .where(
            Approval.id == approval_id,
            Approval.ten_id == tenant_id,
            Approval.status == "pending",
            Approval.expires_at > _now(),
        )
        .values(status=new_status, decided_by=approver_id, decided_at=_now(), decision=decision)
    )
    await db.commit()
    return result.rowcount == 1


async def expire_overdue(db: AsyncSession) -> list[Approval]:
    q = select(Approval).where(Approval.status == "pending", Approval.expires_at <= _now())
    rows = list((await db.execute(q)).scalars())
    for r in rows:
        r.status = "expired"
        r.decided_at = _now()
    await db.commit()
    return rows