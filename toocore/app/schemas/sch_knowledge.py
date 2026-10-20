from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KnowledgeNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: Optional[int] = None
    level: int
    name: str
    icon: Optional[str] = None
    content: Optional[str] = None
    tag: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class KnowledgeTreeResponse(BaseModel):
    nodes: list[KnowledgeNodeOut]