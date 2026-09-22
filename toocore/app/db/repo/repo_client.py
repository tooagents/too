from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.too.z_client import ZClientDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings
from app.schemas.sch_ai import JWType


async def list_clients(db: AsyncConnection, zjwt: JWType) -> List[ZClientDB]:
    table = ZClientDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.is_deleted.is_not(True))
        .order_by(table.c.created_at.desc())
    )
    return models_from_mappings(ZClientDB, list(result.mappings().all()))


async def get_client_by_id(db: AsyncConnection, client_id: UUID, zjwt: JWType) -> Optional[ZClientDB]:
    table = ZClientDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == client_id, table.c.created_by == zjwt.zuid)
    )
    row = result.mappings().one_or_none()
    return model_from_mapping(ZClientDB, row) if row else None


async def create_client(db: AsyncConnection, payload: dict) -> ZClientDB:
    table = ZClientDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(ZClientDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(ZClientDB, result.mappings().one())


async def update_client_fields(db: AsyncConnection, client: ZClientDB, updates: dict) -> ZClientDB:
    if not updates:
        return client
    table = ZClientDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == client.id)
        .values(**coerce_model_values(ZClientDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(ZClientDB, result.mappings().one())
