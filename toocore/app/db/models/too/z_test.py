from datetime import datetime

from sqlalchemy import UUID, Boolean, Date, DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.db_schemas import SCHEMA_TOO_INV, SCHEMA_TOO_GLOBAL

from .z_base import Base, BaseMixin


class ZTestDB(Base, BaseMixin):
    __tablename__ = "ztest"
    __table_args__ = {"schema": SCHEMA_TOO_GLOBAL}

    test1: Mapped[str] = mapped_column(String, nullable=True, default="FIRM")
    test2: Mapped[str] = mapped_column(String, nullable=True, default="my org")

