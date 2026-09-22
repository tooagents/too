from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.too.z_client import ZClientDB
from app.db.repo.repo_client import create_client as repo_create_client
from app.db.repo.repo_client import get_client_by_id, list_clients, update_client_fields
from app.schemas.sch_ai import JWType


async def fetch_clients(zjwt: JWType, db: AsyncConnection) -> list[ZClientDB]:
    return await list_clients(db, zjwt)


async def create_or_update_client(zjwt: JWType, db: AsyncConnection, payload: dict) -> ZClientDB:
    base_ids = {
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zuid,
        "usr_id": zjwt.zuid,
        "cli_id": zjwt.zuid,
        "created_by": zjwt.zuid,
    }
    client_id = payload.get("id")
    if client_id:
        existing = await get_client_by_id(db, client_id, zjwt)
        updates = {k: v for k, v in payload.items() if k != "id"}
        if existing:
            return await update_client_fields(db, existing, updates)
    data = {**base_ids, **payload}
    return await repo_create_client(db, data)
