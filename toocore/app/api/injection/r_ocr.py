from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.api.injection.pdf_processor import process_pdf
from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.db.models.acc.ac_ocr import OcrDocument
from app.schemas.sch_ai import JWType
from app.schemas.sch_ocr import PdfOcrResponse

rouOcr = APIRouter(tags=["ocr"])

OCR_TABLE = OcrDocument.__table__

_ALLOWED_MIME = {
    "application/pdf": "application/pdf",
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/webp": "image/webp",
}


@rouOcr.post("/pdf-to-json", response_model=PdfOcrResponse, status_code=status.HTTP_201_CREATED)
async def pdf_to_json(
    file: UploadFile = File(..., description="PDF or image document to OCR"),
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
) -> PdfOcrResponse:
    """
    OCR an uploaded document with Gemini and store the raw JSON in the database.

    This endpoint:
    - Reads the uploaded file bytes (no file is retained)
    - Sends the document to Gemini for multimodal OCR extraction
    - Stores the raw extraction JSON as JSONB in too_acc.ocr_documents
    """
    mime_type = _ALLOWED_MIME.get((file.content_type or "").lower())
    if mime_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF or PNG/JPEG/WEBP image files are supported",
        )

    try:
        payload = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {exc}",
        ) from exc

    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        result = process_pdf(
            pdf_bytes=payload,
            original_filename=file.filename or "",
            mime_type=mime_type,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {exc}",
        ) from exc

    values = {
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zbid,
        "cli_id": zjwt.zcid,
        "usr_id": zjwt.zuid,
        "created_by": zjwt.zuid,
        "original_filename": file.filename,
        "model_id": result["model_id"],
        "total_pages": result["total_pages"],
        "raw_json": result["raw_json"],
    }

    try:
        row = (
            await db.execute(insert(OCR_TABLE).values(**values).returning(OCR_TABLE))
        ).mappings().one()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving OCR result: {exc}",
        ) from exc

    return PdfOcrResponse(
        id=row["id"],
        original_filename=row["original_filename"],
        model_id=row["model_id"],
        total_pages=row["total_pages"] or 0,
        raw_json=row["raw_json"],
    )
