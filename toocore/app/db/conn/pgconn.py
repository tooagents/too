# For other tables, the same pattern works if all 4 are true:

# Runtime DB user is set by TOO_AIVEN_RLS, normally the restricted usertoo role.
# JWT claims are set per request (request.jwt.claims) with required tenant keys.
# DB privileges exist for that schema/table (USAGE on schema + table grants)
# RLS is enabled + policy exists on each table
# For each new table, do:

# ALTER TABLE ... ENABLE ROW LEVEL SECURITY
# CREATE POLICY ... FOR SELECT ... USING (...)
# Add INSERT/UPDATE/DELETE policies too (WITH CHECK for writes)
# So yes, apply similar policy logic table-by-table, and it will work with your current backend RLS setup.
import json
import logging

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings_singleton
from app.core.auth import get_jwks_decoded
from app.db.conn.db_async import admin_engine  # single shared admin engine

settings = get_settings_singleton()
_log = logging.getLogger("app.http")

RLS_URL = (settings.TOO_AIVEN_RLS or "").strip()
if not RLS_URL: raise RuntimeError("TOO_AIVEN_RLS is not set.")

# RLS engine carries all normal request traffic — the workhorse pool.
# hard cap = pool_size + max_overflow = 8 + 4 = 12 connections
async_engine_rls = create_async_engine(
    RLS_URL,
    pool_pre_ping=True,
    pool_size=8,
    max_overflow=4,
    pool_recycle=1800,
    echo=False,
)

def _claims_for_rls(decoded: dict) -> dict:
    claims = dict(decoded)
    if claims.get("sba_ten_id"):return claims

    app_metadata = claims.get("app_metadata")
    user_metadata = claims.get("user_metadata")
    app_ten_id = app_metadata.get("sba_ten_id") if isinstance(app_metadata, dict) else None
    user_ten_id = user_metadata.get("sba_ten_id") if isinstance(user_metadata, dict) else None
    fallback_ten_id = app_ten_id or user_ten_id
    if not fallback_ten_id:
        raise RuntimeError("RLS requires tenant claim 'sba_ten_id' (top-level or in app_metadata/user_metadata).")

    claims["sba_ten_id"] = fallback_ten_id
    _log.info(
        "RLS claims normalized: sba_ten_id source=%s value=%s",
        "app_metadata" if app_ten_id else "user_metadata",
        fallback_ten_id,
    )
    return claims

async def get_rls_conn(decoded: dict = Depends(get_jwks_decoded),):
    async with async_engine_rls.connect() as conn:  # ① 获得连接
        # await conn.execute(text("SET request.jwt.claims = :claims"),{"claims": json.dumps(decoded)})    # ② 设置RLS
        async with conn.begin():
            claims = _claims_for_rls(decoded)
            await conn.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"),
                {"claims": json.dumps(claims)},
            )
                
            yield conn  # ④ 把连接交给 endpoint
        # ⑤ 退出 conn.begin()，自动 COMMIT
    # ⑥ 退出 connect()，连接归还池



async def get_admin_conn():
    async with admin_engine.connect() as conn:  # ① 获得连接
        async with conn.begin():
            yield conn  # ④ 把连接交给 endpoint
