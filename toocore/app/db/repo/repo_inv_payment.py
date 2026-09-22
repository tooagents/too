from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_nvoice_payment import InvoicePaymentDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings
from app.schemas.sch_ai import JWType


async def list_invoice_payments(db: AsyncConnection, inv_id: UUID) -> List[InvoicePaymentDB]:
    table = InvoicePaymentDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.inv_id == inv_id)
        .order_by(table.c.created_at.desc())
    )
    return models_from_mappings(InvoicePaymentDB, list(result.mappings().all()))


async def get_invoice_payment_by_id(
    db: AsyncConnection, payment_id: UUID, zjwt: JWType
) -> Optional[InvoicePaymentDB]:
    table = InvoicePaymentDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == payment_id)
    )
    row = result.mappings().one_or_none()
    return model_from_mapping(InvoicePaymentDB, row) if row else None


async def create_invoice_payment(db: AsyncConnection, payload: dict) -> InvoicePaymentDB:
    table = InvoicePaymentDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(InvoicePaymentDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(InvoicePaymentDB, result.mappings().one())


async def update_invoice_payment_fields(
    db: AsyncConnection, payment: InvoicePaymentDB, updates: dict
) -> InvoicePaymentDB:
    if not updates:
        return payment
    table = InvoicePaymentDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == payment.id)
        .values(**coerce_model_values(InvoicePaymentDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(InvoicePaymentDB, result.mappings().one())


async def delete_invoice_payment(db: AsyncConnection, payment: InvoicePaymentDB) -> None:
    table = InvoicePaymentDB.__table__
    await db.execute(delete(table).where(table.c.id == payment.id))
