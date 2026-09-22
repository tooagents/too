from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.too.z_note import ZNoteDB
from app.db.repo.repo_note import create_note as repo_create_note
from app.db.repo.repo_note import get_note_by_id, list_notes, update_note_fields
from app.schemas.sch_ai import JWType


async def fetch_notes(zjwt: JWType, db: AsyncConnection) -> list[ZNoteDB]:
    return await list_notes(db, zjwt)


async def create_or_update_note(zjwt: JWType, db: AsyncConnection, payload: dict) -> ZNoteDB:
    base_ids = {
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zuid,
        "usr_id": zjwt.zuid,
        "cli_id": zjwt.zuid,
        "created_by": zjwt.zuid,
    }
    note_id = payload.get("id")
    if note_id:
        existing = await get_note_by_id(db, note_id, zjwt)
        updates = {k: v for k, v in payload.items() if k != "id"}
        if existing:
            return await update_note_fields(db, existing, updates)
    data = {**base_ids, **payload}
    return await repo_create_note(db, data)


async def soft_delete_note(zjwt: JWType, db: AsyncConnection, note_id: UUID) -> ZNoteDB | None:
    existing = await get_note_by_id(db, note_id, zjwt)
    if not existing:
        return None
    return await update_note_fields(db, existing, {"is_deleted": True})
