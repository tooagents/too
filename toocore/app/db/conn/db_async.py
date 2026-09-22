# db_async.py — admin engine (single source of truth for the ADMIN url)
#
# The admin engine is used only by privileged paths that bypass RLS:
# registration/provisioning, seed, employee/me/be/mcp callbacks.
# Registration is rare and bursty, so the pool is intentionally small.
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings_singleton

settings = get_settings_singleton()

ADMIN_URL = (settings.TOO_AIVEN_ADMIN or "").strip()
if not ADMIN_URL:
    raise RuntimeError("TOO_AIVEN_ADMIN is not set.")

# Single admin engine for the whole app. Small pool: admin traffic is low-volume.
# hard cap = pool_size + max_overflow = 1 + 2 = 3 connections
admin_engine = create_async_engine(
    ADMIN_URL,
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=2,
    pool_recycle=1800,  # recycle before Aiven idle-times out connections
    echo=False,
)

AsyncSessionLocal_Admin = async_sessionmaker(admin_engine, expire_on_commit=False)


async def get_db_admin() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal_Admin() as session:
        yield session
