from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_tem import ItemDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings
from app.schemas.sch_ai import JWType


async def list_items(db: AsyncConnection, zjwt: JWType) -> List[ItemDB]:
    table = ItemDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.created_by == zjwt.zuid, table.c.is_deleted.isnot(True))
        .order_by(table.c.created_at.desc())
    )
    return models_from_mappings(ItemDB, list(result.mappings().all()))

async def get_item_by_id(db: AsyncConnection, item_id: UUID, zjwt: JWType) -> Optional[ItemDB]:
    table = ItemDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == item_id, table.c.created_by == zjwt.zuid)
    )
    row = result.mappings().one_or_none()
    return model_from_mapping(ItemDB, row) if row else None


async def create_item(db: AsyncConnection, payload: dict) -> ItemDB:
    table = ItemDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(ItemDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(ItemDB, result.mappings().one())


async def update_item_fields(db: AsyncConnection, item: ItemDB, updates: dict) -> ItemDB:
    if not updates:
        return item
    table = ItemDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == item.id)
        .values(**coerce_model_values(ItemDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(ItemDB, result.mappings().one())
