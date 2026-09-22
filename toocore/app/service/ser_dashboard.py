from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.too.z_be import ZBizEntityDB
from app.db.models.too.z_user import ZUserDB
from app.db.repo.repo_utils import model_from_mapping
from app.schemas.sch_ai import JWType

_log = logging.getLogger(__name__)


async def fetch_homeinfo(
    zjwt: JWType,
    db: AsyncConnection,
) -> tuple[ZUserDB, ZBizEntityDB | None]:
    _log.info("dashboard fetch start sub=%s", zjwt.zuid)
    user_table = ZUserDB.__table__
    user_result = await db.execute(select(user_table).where(user_table.c.id == zjwt.zuid))
    user_row = user_result.mappings().one_or_none()
    user = model_from_mapping(ZUserDB, user_row) if user_row else None
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    be_table = ZBizEntityDB.__table__
    be_result = await db.execute(select(be_table).where(be_table.c.id == zjwt.zuid))
    be_row = be_result.mappings().one_or_none()
    be = model_from_mapping(ZBizEntityDB, be_row) if be_row else None
    return user, be
