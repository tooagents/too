"""Gemini helper for smart invoice cloning.

Cloning a recurring invoice should land the *next* one in the series without the
user editing dates. ``inv_date`` is the ISSUE date. For most invoices there is
no billing period and the next issue date is just a best-effort guess from the
client's recent cadence. But some invoices — typically service billing — state
an explicit SERVICE PERIOD in free text (e.g. "Jan 1-8", "Feb 2 - Feb 22"). That
period can appear anywhere: ``inv_reference``, ``inv_notes``, or a line item's
name/description/note. When a period is present, the issue date must be that
period's ENDING date, and the clone advances to the next period.

Rather than hardcode one cadence, we show Gemini the client's last few invoices
(with their free text and line-item text) and let it (a) find any period, (b)
advance it, and (c) otherwise guess the next issue date.

This never raises: any failure (no key, provider error, bad JSON, low
confidence) returns ``None`` so the caller falls back to a plain verbatim copy.
Cloning is low-stakes and fully editable, so a best-effort guess is enough.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings_singleton

logger = logging.getLogger(__name__)

settings = get_settings_singleton()

# Reuse the same working model the bank AI uses (BANK_AI_MODEL_ID =
# "gemini-flash-latest"); the OCR default "gemini-2.5-flash" 404s for this key.
CLONE_AI_MODEL_ID = (
    getattr(settings, "INV_AI_MODEL_ID", None)
    or getattr(settings, "BANK_AI_MODEL_ID", None)
    or "gemini-flash-latest"
)

_client: genai.Client | None = None


def _get_client() -> genai.Client | None:
    """Lazily build the Gemini client; return None when no key is configured."""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            return None
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _strip_json_fences(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


_SYSTEM_INSTRUCTION = (
    "You are cloning a recurring invoice to the NEXT one in the series. You are "
    "given the client's most recent invoices, ordered NEWEST FIRST. Each has: "
    "inv_reference and inv_notes (free text), item_texts (line-item names / "
    "descriptions / notes), inv_date (the ISSUE date), inv_due_date, and "
    "inv_payment_term (days).\n"
    "\n"
    "Some invoices — typically service billing — state an explicit SERVICE PERIOD "
    "somewhere in their free text: a date range like 'Jan 1-8' or 'Feb 2 - Feb "
    "22'. It may appear in inv_reference, inv_notes, OR item_texts. Most invoices "
    "have no such period.\n"
    "\n"
    "Your job:\n"
    "1. Look for a service period anywhere in the NEWEST invoice's free text.\n"
    "2. If you find one: infer the client's cadence from the recent invoices and "
    "produce the NEXT period following the newest one. Set next_period_end to that "
    "period's ENDING date and period_found = true. The issue date IS the period "
    "ending date, so inv_date = next_period_end.\n"
    "   - If the period was written in inv_reference, set reference_holds_period = "
    "true and put the advanced label in inv_reference, copying the newest "
    "reference's FORMAT exactly (same month/day style, separators, spacing) — only "
    "the dates advance. Otherwise reference_holds_period = false and inv_reference "
    "= null (do NOT invent a reference).\n"
    "3. If you find NO period: period_found = false, reference_holds_period = "
    "false, inv_reference = null, next_period_end = null. Best-effort guess the "
    "next ISSUE date (inv_date) from the pattern of recent inv_date values.\n"
    "\n"
    "Always set inv_due_date = inv_date + inv_payment_term days (use the newest "
    "invoice's term); null if the term is unknown.\n"
    "\n"
    "Return ONLY a JSON object of this EXACT shape (no commentary, no code fences):\n"
    '{ "period_found": true|false, "reference_holds_period": true|false, '
    '"next_period_end": "YYYY-MM-DD"|null, "inv_reference": "next label"|null, '
    '"inv_date": "YYYY-MM-DD", "inv_due_date": "YYYY-MM-DD"|null }'
)


def _coerce_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


async def suggest_next_period(recent: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Infer the next invoice's issue date from a client's recent invoices.

    ``recent`` is newest-first, each item ``{inv_reference, inv_notes,
    item_texts, inv_date, inv_due_date, inv_payment_term}`` (dates as ISO
    strings). Returns ``{inv_reference, inv_date, inv_due_date}`` where:

    - ``inv_date`` is the period ENDING date when a service period was found
      anywhere in the invoice, otherwise a best-effort next issue date.
    - ``inv_reference`` is the advanced label ONLY when the period lived in the
      reference; ``None`` otherwise, signalling the caller to keep its verbatim
      copy of the source reference.

    Returns ``None`` when nothing usable can be inferred, in which case the
    caller copies the source dates verbatim.
    """
    if not recent:
        logger.info("inv smart-clone: no recent invoices -> verbatim copy")
        return None

    client = _get_client()
    if client is None:
        logger.warning(
            "inv smart-clone: GEMINI_API_KEY not configured -> verbatim copy"
        )
        return None

    prompt = (
        "Recent invoices (newest first):\n"
        f"{json.dumps(recent, ensure_ascii=False, indent=2)}\n\n"
        "Produce the next invoice's period as JSON."
    )

    logger.info(
        "inv smart-clone: -> Gemini model=%s, %d recent invoice(s): %s",
        CLONE_AI_MODEL_ID,
        len(recent),
        json.dumps(recent, ensure_ascii=False),
    )

    try:
        response = await client.aio.models.generate_content(
            model=CLONE_AI_MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:  # noqa: BLE001 - any provider failure -> verbatim fallback
        logger.warning("inv smart-clone: Gemini call failed (%s) -> verbatim copy", exc)
        return None

    logger.info("inv smart-clone: <- Gemini raw response: %r", response.text)
    raw = _strip_json_fences(response.text or "")
    if not raw:
        logger.warning("inv smart-clone: Gemini returned empty content -> verbatim copy")
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(
            "inv smart-clone: Gemini returned invalid JSON (%r) -> verbatim copy", raw
        )
        return None
    if not isinstance(parsed, dict):
        logger.warning(
            "inv smart-clone: Gemini JSON was not an object (%r) -> verbatim copy", parsed
        )
        return None

    period_found = bool(parsed.get("period_found"))
    reference_holds_period = bool(parsed.get("reference_holds_period"))
    next_period_end = _coerce_date(parsed.get("next_period_end"))
    guessed_date = _coerce_date(parsed.get("inv_date"))
    inv_due_date = _coerce_date(parsed.get("inv_due_date"))
    inv_reference = parsed.get("inv_reference")

    # The issue date is the period's ENDING date when a period was found;
    # otherwise fall back to the model's best-effort next issue date.
    inv_date = next_period_end if (period_found and next_period_end) else guessed_date
    # Need at least a usable issue date to be worth overriding the copy.
    if inv_date is None:
        logger.warning(
            "inv smart-clone: Gemini gave no usable inv_date (%r) -> verbatim copy", parsed
        )
        return None

    # Only override the (verbatim-copied) reference when the period actually
    # lived in it. For free-text references we leave the caller's copy untouched.
    next_reference = (
        str(inv_reference).strip()
        if (period_found and reference_holds_period and inv_reference and str(inv_reference).strip())
        else None
    )

    logger.info(
        "inv smart-clone: inferred -> inv_date=%s (period_found=%s, ref=%r, due %s)",
        inv_date, period_found, next_reference, inv_due_date,
    )
    return {
        "inv_reference": next_reference,
        "inv_date": inv_date,
        "inv_due_date": inv_due_date,
    }
