from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.too.z_note import ZNoteDB
from app.schemas.sch_ai import JWType
from app.schemas.sch_note import NoteCreate, NoteOut
from app.service.ser_note import create_or_update_note, fetch_notes, soft_delete_note

noteRou = APIRouter()


def _to_out(note: ZNoteDB) -> NoteOut:
    return NoteOut(
        id=note.id,
        title=note.note_title,
        color=note.note_color,
        datef=note.created_at,
        deleted=bool(note.is_deleted),
    )


def _to_db(payload: NoteCreate) -> dict:
    data = payload.model_dump(exclude_unset=True)
    mapped: dict = {}
    if "id" in data:
        mapped["id"] = data["id"]
    if "title" in data:
        mapped["note_title"] = data["title"]
    if "color" in data:
        mapped["note_color"] = data["color"]
    return mapped


@noteRou.get("/get_note_list", response_model=list[NoteOut])
async def get_notes(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    notes = await fetch_notes(zjwt, db)
    return [_to_out(note) for note in notes]


@noteRou.post("/post_note", response_model=NoteOut)
async def post_note(
    payload: NoteCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    note = await create_or_update_note(zjwt, db, _to_db(payload))
    return _to_out(note)


@noteRou.post("/delete_note/{note_id}", response_model=NoteOut)
async def delete_note(
    note_id: UUID,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    note = await soft_delete_note(zjwt, db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return _to_out(note)
