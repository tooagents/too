from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_tem import ItemDB
from app.db.repo.repo_item import create_item as repo_create_item
from app.db.repo.repo_item import get_item_by_id, list_items, update_item_fields
from app.schemas.sch_ai import JWType


async def fetch_items(zjwt: JWType, db: AsyncConnection) -> list[ItemDB]:
    return await list_items(db, zjwt)


async def create_or_update_item(zjwt: JWType, db: AsyncConnection, payload: dict) -> ItemDB:
    base_ids = {
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zuid,
        "usr_id": zjwt.zuid,
        "cli_id": zjwt.zcid,
        "created_by": zjwt.zuid,
    }
    item_id = payload.get("id")
    if item_id:
        existing = await get_item_by_id(db, item_id, zjwt)
        updates = {k: v for k, v in payload.items() if k != "id"}
        if existing:
            return await update_item_fields(db, existing, updates)
    data = {**base_ids, **payload}
    return await repo_create_item(db, data)


async def soft_delete_item(zjwt: JWType, db: AsyncConnection, item_id) -> None:
    existing = await get_item_by_id(db, item_id, zjwt)
    if not existing:
        raise ValueError("Item not found")
    await update_item_fields(db, existing, {"is_deleted": True})
