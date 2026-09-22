from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_nvoice import InvoiceDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings


async def list_invoices(db: AsyncConnection) -> List[InvoiceDB]:
    table = InvoiceDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.is_deleted.is_not(True))
        .order_by(table.c.created_at.desc())
    )
    return models_from_mappings(InvoiceDB, list(result.mappings().all()))


async def list_recent_invoices_by_client(
    db: AsyncConnection,
    *,
    client_id: Optional[UUID] = None,
    client_email: Optional[str] = None,
    client_company_name: Optional[str] = None,
    limit: int = 3,
) -> List[InvoiceDB]:
    """Most-recent non-deleted invoices for one client, newest issue-date first.

    Used by the smart-clone flow to infer the client's recurring billing pattern
    (cadence + reference-label format) from its latest few invoices. The client
    FK (``client_id``) is often null on invoices, so we match on whatever client
    identity the invoice actually carries: prefer the FK, then email (case-
    insensitive), then company name. Tenant scoping comes from the RLS
    connection. Returns [] when there's no usable identity to match on.
    """
    table = InvoiceDB.__table__
    if client_id is not None:
        match = table.c.client_id == client_id
    elif client_email and client_email.strip():
        match = func.lower(table.c.client_email) == client_email.strip().lower()
    elif client_company_name and client_company_name.strip():
        match = table.c.client_company_name == client_company_name.strip()
    else:
        return []

    result = await db.execute(
        select(table)
        .where(table.c.is_deleted.is_not(True))
        .where(match)
        .order_by(table.c.inv_date.desc().nullslast(), table.c.created_at.desc())
        .limit(limit)
    )
    return models_from_mappings(InvoiceDB, list(result.mappings().all()))


async def get_invoice_by_id(db: AsyncConnection, inv_id: UUID) -> Optional[InvoiceDB]:
    table = InvoiceDB.__table__
    result = await db.execute(select(table).where(table.c.id == inv_id))
    row = result.mappings().one_or_none()
    return model_from_mapping(InvoiceDB, row) if row else None


async def create_invoice(db: AsyncConnection, payload: dict) -> InvoiceDB:
    table = InvoiceDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(InvoiceDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(InvoiceDB, result.mappings().one())


async def update_invoice_fields(
    db: AsyncConnection, inv: InvoiceDB, updates: dict
) -> InvoiceDB:
    if not updates:
        return inv
    table = InvoiceDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == inv.id)
        .values(**coerce_model_values(InvoiceDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(InvoiceDB, result.mappings().one())


# ---------- reconciliation (invoice-level bank_txn link = source of truth) ----------


async def invoice_ids_reconciled_to(
    db: AsyncConnection, bank_txn_ids: list[UUID]
) -> dict[UUID, list[UUID]]:
    """Invoice ids reconciled to each deposit, from the invoice-level link (not payments)."""
    if not bank_txn_ids:
        return {}
    t = InvoiceDB.__table__
    result = await db.execute(
        select(t.c.reconciled_bank_txn_id, t.c.id)
        .where(
            t.c.reconciled_bank_txn_id.in_(bank_txn_ids),
            t.c.is_deleted.is_not(True),
        )
        .order_by(t.c.created_at.asc())
    )
    out: dict[UUID, list[UUID]] = {}
    for bank_txn_id, inv_id in result.all():
        out.setdefault(bank_txn_id, []).append(inv_id)
    return out


async def set_invoice_reconciliation(
    db: AsyncConnection, inv_id: UUID, bank_txn_id: Optional[UUID], reconciled: bool
) -> None:
    """Set/clear an invoice's reconcile link + flag (the reconciliation record)."""
    table = InvoiceDB.__table__
    await db.execute(
        update(table)
        .where(table.c.id == inv_id)
        .values(is_reconciled=reconciled, reconciled_bank_txn_id=bank_txn_id)
    )


async def clear_invoice_reconciliation_for_bank_txn(
    db: AsyncConnection, bank_txn_id: UUID
) -> list[UUID]:
    """Unreconcile every invoice currently linked to this deposit. Returns their ids."""
    table = InvoiceDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.reconciled_bank_txn_id == bank_txn_id)
        .values(is_reconciled=False, reconciled_bank_txn_id=None)
        .returning(table.c.id)
    )
    return [row[0] for row in result.all()]
