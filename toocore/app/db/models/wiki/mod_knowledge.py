from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.conn.pgconn import Base  # 换成你项目里实际的 Base


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(100))
    content: Mapped[Optional[str]] = mapped_column(Text)
    tag: Mapped[Optional[str]] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )