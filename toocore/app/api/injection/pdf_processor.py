"""PDF processor: extracts document content as raw JSON via Gemini multimodal OCR."""

import json
import re
import time
from pathlib import Path, PurePosixPath

from google import genai
from google.genai import types

from app.config import get_settings_singleton

settings = get_settings_singleton()

OCR_MODEL_ID = settings.OCR_MODEL_ID
MAX_PAGES = settings.OCR_MAX_PAGES

OCR_SYSTEM = (Path(__file__).parent / "pdf_ocr.txt").read_text(encoding="utf-8")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazily build the Gemini client so import never fails without a key."""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _log_ocr_event(event: str, **fields) -> None:
    print(
        "[Accounting Intake] "
        + json.dumps({"event": event, **fields}, default=str)
    )


def _sanitise_stem(name: str) -> str:
    """Turn an arbitrary filename into a safe stem."""
    stem = PurePosixPath(name).stem.strip()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    stem = stem.strip("._-")
    return stem or "document"


def _strip_json_fences(text: str) -> str:
    """Gemini occasionally wraps JSON in ```json fences despite instructions."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


def process_pdf(
    pdf_bytes: bytes,
    original_filename: str = "",
    mime_type: str = "application/pdf",
) -> dict:
    """Run OCR over a document and return the raw extraction JSON.

    The full document is sent to Gemini in a single multimodal request; the model
    returns a JSON object describing every page (text, tables, figures). No file is
    persisted — the caller stores the returned JSON.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw bytes of the uploaded document (PDF or image).
    original_filename : str
        Human-readable filename the user uploaded (e.g. "dossier.pdf").
    mime_type : str
        MIME type of the payload. Defaults to application/pdf.

    Returns
    -------
    dict
        Dictionary containing:
        - raw_json: the parsed OCR JSON object from the model
        - total_pages: number of pages the model reported
        - model_id: the model used
        - stem: sanitised filename stem
    """
    stem = _sanitise_stem(original_filename) if original_filename else "document"
    start = time.time()
    _log_ocr_event(
        "llm_start",
        step="process_pdf_ocr",
        model_id=OCR_MODEL_ID,
        original_filename=original_filename,
        mime_type=mime_type,
        input_bytes=len(pdf_bytes),
    )

    try:
        response = _get_client().models.generate_content(
            model=OCR_MODEL_ID,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type=mime_type),
                "Extract all content from this document as JSON per the system instructions.",
            ],
            config=types.GenerateContentConfig(
                system_instruction=OCR_SYSTEM,
                temperature=0,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        _log_ocr_event(
            "llm_error",
            step="process_pdf_ocr",
            model_id=OCR_MODEL_ID,
            elapsed_seconds=round(time.time() - start, 3),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    text = _strip_json_fences(response.text or "")
    try:
        raw_json = json.loads(text)
    except json.JSONDecodeError as exc:
        _log_ocr_event(
            "llm_parse_error",
            step="process_pdf_ocr",
            model_id=OCR_MODEL_ID,
            elapsed_seconds=round(time.time() - start, 3),
            error=str(exc),
            output_chars=len(text),
        )
        raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc

    pages = raw_json.get("pages") if isinstance(raw_json, dict) else None
    total_pages = len(pages) if isinstance(pages, list) else 0
    if total_pages > MAX_PAGES:
        _log_ocr_event(
            "page_limit_exceeded",
            step="process_pdf_ocr",
            model_id=OCR_MODEL_ID,
            reported_pages=total_pages,
            max_pages=MAX_PAGES,
        )

    _log_ocr_event(
        "llm_end",
        step="process_pdf_ocr",
        model_id=OCR_MODEL_ID,
        total_pages=total_pages,
        output_chars=len(text),
        elapsed_seconds=round(time.time() - start, 3),
    )

    return {
        "raw_json": raw_json,
        "total_pages": total_pages,
        "model_id": OCR_MODEL_ID,
        "stem": stem,
    }
