from typing import Any

from sqlalchemy import Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.db_schemas import SCHEMA_TOO_ACC
from app.db.models.too.z_base import Base, BaseMixin


class OcrDocument(Base, BaseMixin):
    """Raw OCR output from a document (PDF/image), stored as JSONB.

    The original file is not retained — only the model's raw extraction JSON.
    """

    __tablename__ = "ocr_documents"
    __table_args__ = {"schema": SCHEMA_TOO_ACC}

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
