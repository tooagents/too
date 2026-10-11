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


def _like_escape(text: str) -> str:
    """Escape LIKE wildcards so a prefix is matched literally.

    Prefixes legitimately contain ``_`` (e.g. ``MO_``), which is a single-char
    LIKE wildcard; without escaping, ``MO_%`` would also match ``MOX...``.
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def max_invoice_integer_for_prefix(db: AsyncConnection, prefix: str) -> int | None:
    """Largest trailing integer among non-deleted invoices whose number is this
    ``prefix`` immediately followed by digits, for the current tenant.

    Tenant scoping comes from the RLS connection. Returns ``None`` when nothing
    matches. Used to base the next auto-generated number on the biggest number
    ACTUALLY in use rather than a stored counter that can drift out of sync with
    the invoices table (ahead when the latest invoices are deleted, behind when
    numbers are hand-edited larger).
    """
    table = InvoiceDB.__table__
    result = await db.execute(
        select(table.c.inv_number)
        .where(table.c.is_deleted.is_not(True))
        .where(table.c.inv_number.is_not(None))
        .where(table.c.inv_number.like(f"{_like_escape(prefix)}%", escape="\\"))
    )
    biggest: int | None = None
    for (number,) in result.all():
        # LIKE narrows the scan; this confirms an exact prefix + pure-digit tail.
        if not number or not number.startswith(prefix):
            continue
        suffix = number[len(prefix):]
        if suffix.isdigit():
            value = int(suffix)
            if biggest is None or value > biggest:
                biggest = value
    return biggest


async def invoice_number_exists(db: AsyncConnection, inv_number: str) -> bool:
    """True when a non-deleted invoice already uses this number for the tenant.

    Mirrors the partial unique index uq_too_inv_invoice_ten_number (ten_id,
    inv_number WHERE is_deleted IS NOT TRUE AND inv_number IS NOT NULL); tenant
    scoping comes from the RLS connection. Used to skip numbers that are already
    taken when auto-generating the next one, now that numbers are user-editable
    and the stored counter can collide with a hand-entered number.
    """
    if not inv_number:
        return False
    table = InvoiceDB.__table__
    result = await db.execute(
        select(table.c.id)
        .where(table.c.inv_number == inv_number)
        .where(table.c.is_deleted.is_not(True))
        .limit(1)
    )
    return result.first() is not None


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
