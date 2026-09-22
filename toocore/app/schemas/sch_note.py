from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NoteOut(BaseModel):
    id: UUID
    title: Optional[str] = None
    color: Optional[str] = None
    datef: Optional[datetime] = None
    deleted: bool = False


class NoteCreate(BaseModel):
    id: Optional[UUID] = None
    title: Optional[str] = None
    color: Optional[str] = None
