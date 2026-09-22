from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.too.z_base import Base, BaseMixin
from app.db.models.db_schemas import SCHEMA_TOO_GLOBAL


class ZNoteDB(Base, BaseMixin):
    __tablename__ = "znote"
    __table_args__ = {"schema": SCHEMA_TOO_GLOBAL}

    note_title: Mapped[str | None] = mapped_column(String)
    note_color: Mapped[str | None] = mapped_column(String(32), default="primary")
