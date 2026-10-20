from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.langgraph.sse.lgstream import build_langgraph_sse_response
from app.schemas.sch_ai import JWType
from app.schemas.sch_ai_rag_basic import RagRerankAnswerResponse
from app.schemas.sch_ai_feedback import FeedbackCreateRequest, FeedbackCreateResponse
from app.schemas.sch_ai_router import RouterQueryRequest
from app.service.ser_ai_feedback import log_feedback_event
from app.service.ser_ai_router import route_and_answer as route_and_answer_service



wikiRou = APIRouter()
logger = logging.getLogger("app.http")


from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.conn.db_async import get_db_admin
from app.db.models.db_schemas import SCHEMA_TOO_WIKI
from sqlalchemy.ext.asyncio import AsyncSession


class KnowledgeNodeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str | None = None


@wikiRou.get("/tree")
async def get_knowledge_tree(
    db: AsyncSession = Depends(get_db_admin),
):
    try:
        result = await db.execute(
            text(f"""
                SELECT id, parent_id, level, name, icon, content, tag, sort_order
                FROM {SCHEMA_TOO_WIKI}.knowledge_nodes
                ORDER BY level, sort_order, id
            """)
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to load wiki knowledge tree")
        raise HTTPException(
            status_code=503,
            detail="Wiki data is temporarily unavailable",
        ) from exc

    return {"nodes": [dict(r) for r in result.mappings().all()]}


@wikiRou.put("/node/{node_id}")
async def update_knowledge_node(
    node_id: int,
    update: KnowledgeNodeUpdate,
    db: AsyncSession = Depends(get_db_admin),
):
    try:
        result = await db.execute(
            text(f"""
                UPDATE {SCHEMA_TOO_WIKI}.knowledge_nodes
                SET name = :name, content = :content, updated_at = now()
                WHERE id = :node_id
                RETURNING id, parent_id, level, name, icon, content, tag, sort_order
            """),
            {"node_id": node_id, "name": update.name, "content": update.content},
        )
        node = result.mappings().first()
        if node is None:
            raise HTTPException(status_code=404, detail="Wiki article not found")
        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to update wiki node %s", node_id)
        raise HTTPException(
            status_code=503,
            detail="Wiki data could not be saved",
        ) from exc

    return {"node": dict(node)}
