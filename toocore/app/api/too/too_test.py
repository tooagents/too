from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.too.z_test import ZTestDB
from app.schemas.sch_ai import JWType

testRou = APIRouter()


def _to_db_dict(record: ZTestDB) -> dict[str, Any]:
    return {column.name: getattr(record, column.name) for column in record.__table__.columns}


@testRou.get("/ztest", response_model=list[dict[str, Any]])
async def get_ztest_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_rls_conn),
):
    result = await db.execute(select(ZTestDB).order_by(ZTestDB.created_at.desc()))
    return [_to_db_dict(record) for record in result.scalars().all()]
