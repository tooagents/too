from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_nvoice_item import InvoiceItemDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings


async def list_invoice_items(db: AsyncConnection, inv_id: UUID) -> List[InvoiceItemDB]:
    table = InvoiceItemDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.inv_id == inv_id)
        .order_by(table.c.created_at.desc())
    )
    return models_from_mappings(InvoiceItemDB, list(result.mappings().all()))


async def delete_invoice_items(db: AsyncConnection, inv_id: UUID) -> None:
    """Hard-delete every line item for an invoice (used to resync on save)."""
    table = InvoiceItemDB.__table__
    await db.execute(delete(table).where(table.c.inv_id == inv_id))


async def create_invoice_item(db: AsyncConnection, payload: dict) -> InvoiceItemDB:
    table = InvoiceItemDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(InvoiceItemDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(InvoiceItemDB, result.mappings().one())
