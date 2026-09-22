from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.acc.o_bank_txn import OBankTxn
from app.db.models.inv.i_nvoice_payment import InvoicePaymentDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings


async def list_bank_txns(db: AsyncConnection) -> List[OBankTxn]:
    table = OBankTxn.__table__
    result = await db.execute(
        select(table)
        .where(table.c.is_deleted.is_not(True))
        .order_by(table.c.txn_date.desc(), table.c.created_at.desc())
    )
    return models_from_mappings(OBankTxn, list(result.mappings().all()))


async def get_bank_txn_by_id(db: AsyncConnection, txn_id: UUID) -> Optional[OBankTxn]:
    table = OBankTxn.__table__
    result = await db.execute(select(table).where(table.c.id == txn_id))
    row = result.mappings().one_or_none()
    return model_from_mapping(OBankTxn, row) if row else None


async def create_bank_txn(db: AsyncConnection, payload: dict) -> OBankTxn:
    table = OBankTxn.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(OBankTxn, payload))
        .returning(*table.c)
    )
    return model_from_mapping(OBankTxn, result.mappings().one())


async def update_bank_txn_fields(db: AsyncConnection, txn: OBankTxn, updates: dict) -> OBankTxn:
    if not updates:
        return txn
    table = OBankTxn.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == txn.id)
        .values(**coerce_model_values(OBankTxn, updates))
        .returning(*table.c)
    )
    return model_from_mapping(OBankTxn, result.mappings().one())


async def soft_delete_bank_txn(db: AsyncConnection, txn: OBankTxn) -> None:
    """Mark a bank transaction as deleted (mirrors JE soft-delete)."""
    table = OBankTxn.__table__
    await db.execute(
        update(table)
        .where(table.c.id == txn.id)
        .values(is_deleted=True)
    )


async def applied_totals_by_bank_txn(
    db: AsyncConnection, bank_txn_ids: list[UUID]
) -> dict[UUID, Decimal]:
    """Sum of pay_amount grouped by bank_txn_id (excludes soft-deleted payments)."""
    if not bank_txn_ids:
        return {}
    t = InvoicePaymentDB.__table__
    result = await db.execute(
        select(t.c.bank_txn_id, func.coalesce(func.sum(t.c.pay_amount), 0))
        .where(t.c.bank_txn_id.in_(bank_txn_ids), t.c.is_deleted.is_not(True))
        .group_by(t.c.bank_txn_id)
    )
    return {row[0]: Decimal(str(row[1])) for row in result.all()}


async def invoice_ids_by_bank_txn(
    db: AsyncConnection, bank_txn_ids: list[UUID]
) -> dict[UUID, list[UUID]]:
    """Invoice ids paid by each deposit (excludes soft-deleted payments)."""
    if not bank_txn_ids:
        return {}
    t = InvoicePaymentDB.__table__
    result = await db.execute(
        select(t.c.bank_txn_id, t.c.inv_id)
        .where(t.c.bank_txn_id.in_(bank_txn_ids), t.c.is_deleted.is_not(True))
        .order_by(t.c.created_at.asc())
    )
    out: dict[UUID, list[UUID]] = {}
    for bank_txn_id, inv_id in result.all():
        out.setdefault(bank_txn_id, []).append(inv_id)
    return out


async def payments_for_bank_txn(db: AsyncConnection, bank_txn_id: UUID) -> List[InvoicePaymentDB]:
    """All (non-deleted) payment rows linked to a given deposit."""
    t = InvoicePaymentDB.__table__
    result = await db.execute(
        select(t)
        .where(t.c.bank_txn_id == bank_txn_id, t.c.is_deleted.is_not(True))
        .order_by(t.c.created_at.asc())
    )
    return models_from_mappings(InvoicePaymentDB, list(result.mappings().all()))
