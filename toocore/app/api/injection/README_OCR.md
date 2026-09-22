# PDF OCR API Endpoint

## Overview
This module provides a FastAPI endpoint that OCRs an uploaded document (PDF or image) using Gemini multimodal extraction and stores the raw JSON result in the database. The original file is not retained.

## Files
- `r_ocr.py` - FastAPI router with the upload endpoint
- `pdf_processor.py` - Core OCR processing logic (Gemini)
- `pdf_ocr.txt` - System prompt for OCR extraction (instructs JSON output)
- `app/schemas/sch_ocr.py` - Pydantic response model
- `app/db/models/acc/ac_ocr.py` - `OcrDocument` SQLAlchemy model (too_acc.ocr_documents)

## Endpoint

### `POST /ocr/pdf-to-json`

OCRs an uploaded document and stores the raw extraction JSON as JSONB.

**Request:** `multipart/form-data` with a `file` field (PDF or PNG/JPEG/WEBP).

**Response:**
```json
{
  "id": "uuid-of-stored-row",
  "original_filename": "report.pdf",
  "model_id": "gemini-2.5-flash",
  "total_pages": 15,
  "raw_json": { "pages": [ { "page": 1, "text": "...", "tables": [], "figures": [] } ] }
}
```

**Authentication:** Requires JWT token (via `get_zjwt`), stored under the caller's tenant (RLS).

## Environment Variables

Required:
- `GEMINI_API_KEY` - API key for the Gemini client

Optional:
- `OCR_MODEL_ID` - Gemini model ID (default: `gemini-2.5-flash`)
- `OCR_MAX_PAGES` - Soft page limit for logging (default: 200)

## Flow

1. Client uploads a PDF/image (multipart)
2. Bytes are sent to Gemini in a single multimodal request (PDF read natively)
3. Model returns a JSON object describing every page (text, tables, figures)
4. Raw JSON is stored as JSONB in `too_acc.ocr_documents`

## Storage

The `too_acc.ocr_documents` table (see migration `o_c3d4e5f6a7b8_create_ocr_documents`)
holds `raw_json` (JSONB) plus `original_filename`, `model_id`, and `total_pages`,
inheriting the standard tenancy columns from `BaseMixin`.

## Dependencies

```
google-genai
fastapi
pydantic
sqlalchemy
```

## Error Handling

- `400` - Unsupported/empty file
- `500` - Missing `GEMINI_API_KEY`
- `500` - Gemini API errors / invalid JSON from model
- `500` - Database insert errors
