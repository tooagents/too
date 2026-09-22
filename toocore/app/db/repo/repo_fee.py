from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_fee import FeeDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings
from app.schemas.sch_ai import JWType


async def list_fees(db: AsyncConnection, zjwt: JWType) -> List[FeeDB]:
    table = FeeDB.__table__
    result = await db.execute(
        select(table).order_by(table.c.created_at.desc())
    )
    return models_from_mappings(FeeDB, list(result.mappings().all()))

async def get_fee_by_id(db: AsyncConnection, fee_id: UUID, zjwt: JWType) -> Optional[FeeDB]:
    table = FeeDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == fee_id, table.c.created_by == zjwt.zuid)
    )
    row = result.mappings().one_or_none()
    return model_from_mapping(FeeDB, row) if row else None


async def create_fee(db: AsyncConnection, payload: dict) -> FeeDB:
    table = FeeDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(FeeDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(FeeDB, result.mappings().one())


async def update_fee_fields(db: AsyncConnection, fee: FeeDB, updates: dict) -> FeeDB:
    if not updates:
        return fee
    table = FeeDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == fee.id)
        .values(**coerce_model_values(FeeDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(FeeDB, result.mappings().one())
