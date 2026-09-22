from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_tax import TaxDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings
from app.schemas.sch_ai import JWType

_log = logging.getLogger("app.http")


async def list_taxes(db: AsyncConnection, zjwt: JWType) -> List[TaxDB]:
    table = TaxDB.__table__
    result = await db.execute(
        select(table).order_by(table.c.created_at.desc())
    )
    rows = models_from_mappings(TaxDB, list(result.mappings().all()))
    _log.info("list_taxes result_count=%s zuid=%s", len(rows), zjwt.zuid)
    return rows

async def get_tax_by_id(db: AsyncConnection, tax_id: UUID, zjwt: JWType) -> Optional[TaxDB]:
    table = TaxDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == tax_id, table.c.created_by == zjwt.zuid)
    )
    row = result.mappings().one_or_none()
    return model_from_mapping(TaxDB, row) if row else None


async def create_tax(db: AsyncConnection, payload: dict) -> TaxDB:
    table = TaxDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(TaxDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(TaxDB, result.mappings().one())


async def update_tax_fields(db: AsyncConnection, tax: TaxDB, updates: dict) -> TaxDB:
    if not updates:
        return tax
    table = TaxDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == tax.id)
        .values(**coerce_model_values(TaxDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(TaxDB, result.mappings().one())
