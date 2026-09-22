from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PdfOcrResponse(BaseModel):
    id: UUID = Field(..., description="ID of the stored ocr_documents row")
    original_filename: str | None = Field(None, description="Uploaded filename")
    model_id: str | None = Field(None, description="OCR model used")
    total_pages: int = Field(..., description="Number of pages the model reported")
    raw_json: dict[str, Any] = Field(..., description="Raw OCR extraction JSON")
