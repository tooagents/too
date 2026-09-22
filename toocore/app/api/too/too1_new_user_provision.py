import logging

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_jwks_decoded
from app.db.conn.pgconn import get_admin_conn
from app.service.ser1_new_user import provision_new_user_with_seed
from app.schemas.sch_ai import JWType
from app.core.auth import get_zjwt

newUserRou = APIRouter()
_log = logging.getLogger(__name__)


# @newUserRou.post("/r1_new_user_provision", response_class=PlainTextResponse)
# async def post_profile(
#     decoded: dict = Depends(get_jwks_decoded),
#     db: AsyncSession = Depends(get_db_admin),
# ):
#     try:
#         await provision_new_user(decoded, db)
#     except Exception:raise
#     return "success"


# @newUserRou.post("/r1_new_user_provision_with_seed", response_class=PlainTextResponse)
# async def post_profile2(
#     decoded: dict = Depends(get_jwks_decoded),
#     db: AsyncSession = Depends(get_db_admin),
# ):
#     try:
#         await provision_new_user_with_seed(decoded, db)
#     except Exception:raise
#     return "success"

@newUserRou.post("/new_user_provision_seed", response_class=PlainTextResponse)
async def post_profile_zjwt(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_admin_conn),
):
    try:
        await provision_new_user_with_seed(zjwt, db)
    except Exception:raise
    return "success"

