from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mod_knowledge import KnowledgeNode


async def fetch_all_nodes(db: AsyncSession) -> list[KnowledgeNode]:
    stmt = (
        select(KnowledgeNode)
        .order_by(KnowledgeNode.level, KnowledgeNode.sort_order, KnowledgeNode.id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())