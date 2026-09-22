from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.too.z_note import ZNoteDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings
from app.schemas.sch_ai import JWType


async def list_notes(db: AsyncConnection, zjwt: JWType) -> List[ZNoteDB]:
    table = ZNoteDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.is_deleted.is_not(True))
        .order_by(table.c.created_at.desc())
    )
    return models_from_mappings(ZNoteDB, list(result.mappings().all()))


async def get_note_by_id(db: AsyncConnection, note_id: UUID, zjwt: JWType) -> Optional[ZNoteDB]:
    # Tenant-scoped lookup (RLS on the connection enforces the tenant boundary),
    # matching list_notes which shows all of the tenant's notes. This lets any
    # note in the tenant be updated/deleted, including seeded ones.
    table = ZNoteDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == note_id)
    )
    row = result.mappings().one_or_none()
    return model_from_mapping(ZNoteDB, row) if row else None


async def create_note(db: AsyncConnection, payload: dict) -> ZNoteDB:
    table = ZNoteDB.__table__
    result = await db.execute(
        insert(table)
        .values(**coerce_model_values(ZNoteDB, payload))
        .returning(*table.c)
    )
    return model_from_mapping(ZNoteDB, result.mappings().one())


async def update_note_fields(db: AsyncConnection, note: ZNoteDB, updates: dict) -> ZNoteDB:
    if not updates:
        return note
    table = ZNoteDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == note.id)
        .values(**coerce_model_values(ZNoteDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(ZNoteDB, result.mappings().one())
