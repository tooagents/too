from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Identity, Numeric, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.too.z_base import Base, BaseMixin
from app.db.models.db_schemas import SCHEMA_TOO_ACC


class JournalEntryDB(Base, BaseMixin):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint("source in ('manual','ai','import','reversal')", name="ck_journal_entries_source"),
        UniqueConstraint("ten_id", "entry_no", name="uq_journal_entries_owner_entry_no"),
        {"schema": SCHEMA_TOO_ACC}
    )

    entry_no: Mapped[int] = mapped_column(Identity(always=True), nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=True)
    entry_status: Mapped[str] = mapped_column(String(20), nullable=True, server_default=text("'Draft'"))
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=True, server_default=text("'manual'"))
    source_ref_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    posted_by: Mapped[UUID] = mapped_column(Uuid, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    period_yyyymm: Mapped[int] = mapped_column(nullable=True)
    is_reversal: Mapped[bool] = mapped_column(nullable=True, server_default=text("false"))
    reversed_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{SCHEMA_TOO_ACC}.journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )


class JournalEntryLine(Base, BaseMixin):
    __tablename__ = "journal_entry_lines"
    __table_args__ = (
        CheckConstraint("line_type in ('Debit','Credit')", name="ck_journal_entry_lines_line_type"),
        CheckConstraint("amount > 0", name="ck_journal_entry_lines_amount_positive"),
        {"schema": SCHEMA_TOO_ACC}
    )

    journal_entry_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{SCHEMA_TOO_ACC}.journal_entries.id", ondelete="CASCADE"),
        nullable=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA_TOO_ACC}.coa.id", ondelete="RESTRICT"), nullable=True
    )
    line_type: Mapped[str] = mapped_column(String(10), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=True)


class PeriodCloseDB(Base, BaseMixin):
    __tablename__ = "period_closes"
    __table_args__ = (UniqueConstraint("ten_id", "period_yyyymm", name="uq_period_closes_owner_period"), {"schema": SCHEMA_TOO_ACC})

    period_yyyymm: Mapped[int] = mapped_column(nullable=True)
    is_closed: Mapped[bool] = mapped_column(nullable=True, server_default=text("false"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class AuditEventDB(Base, BaseMixin):
    __tablename__ = "audit_events"
    __table_args__ = {"schema": SCHEMA_TOO_ACC}

    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
