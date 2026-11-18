# app/lgraph/langgraph_search/hitl_approvals.py
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, Uuid, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas.sch_ai import JWType


class Base(DeclarativeBase):          # replace with your project's existing Base
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # who / where (all from the JWT at request time)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    biz_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    requester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    requester_email: Mapped[str | None] = mapped_column(String)

    # which paused graph run this belongs to
    thread_id: Mapped[str] = mapped_column(String, index=True)

    # what needs approving (generic: "sql_query", "refund", "data_export", ...)
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    # lifecycle
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSON)


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
        tenant_id=jwt.ztid,
        biz_id=jwt.zbid,
        customer_id=jwt.zcid,
        requester_id=jwt.zuid,
        requester_email=jwt.zemail,
        thread_id=thread_id,
        kind=kind,
        payload=payload,
        expires_at=_now() + timedelta(days=ttl_days),
    )
    db.add(row)
    await db.commit()          # must be durable BEFORE the graph pauses
    await db.refresh(row)
    return row


async def get_approval(
    db: AsyncSession, approval_id: uuid.UUID, tenant_id: uuid.UUID | None
) -> Approval | None:
    q = select(Approval).where(
        Approval.id == approval_id, Approval.tenant_id == tenant_id
    )
    return (await db.execute(q)).scalar_one_or_none()


async def list_pending(db: AsyncSession, tenant_id: uuid.UUID | None) -> list[Approval]:
    q = (
        select(Approval)
        .where(Approval.tenant_id == tenant_id, Approval.status == "pending")
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
    """One-time transition pending -> approved/rejected.

    Returns False if it was already decided or expired, so a double-click or a
    late click can never trigger a second resume.
    """
    result = await db.execute(
        update(Approval)
        .where(
            Approval.id == approval_id,
            Approval.tenant_id == tenant_id,
            Approval.status == "pending",
            Approval.expires_at > _now(),
        )
        .values(
            status=new_status,
            decided_by=approver_id,
            decided_at=_now(),
            decision=decision,
        )
    )
    await db.commit()
    return result.rowcount == 1


async def expire_overdue(db: AsyncSession) -> list[Approval]:
    """Flip overdue pending rows to 'expired' and return them (for a scheduled job)."""
    q = select(Approval).where(
        Approval.status == "pending", Approval.expires_at <= _now()
    )
    rows = list((await db.execute(q)).scalars())
    for r in rows:
        r.status = "expired"
        r.decided_at = _now()
    await db.commit()
    return rows