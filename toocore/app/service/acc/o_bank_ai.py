"""Gemini interpreter for free-form / pasted bank statement text.

The bank statement composer lets a human paste rows or key in transactions in
whatever shape their bank produced (tab/space/comma columns, or loose natural
language). This turns that text into structured bank-transaction rows the
reconcile flow understands, using the same Gemini client the OCR path uses.
"""

from __future__ import annotations

import itertools
import json
import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from groq import AsyncGroq

from app.config import get_settings_singleton

settings = get_settings_singleton()
logger = logging.getLogger("app.acc.ai")

# Reuse the OCR model unless a dedicated one is configured.
BANK_AI_MODEL_ID = getattr(settings, "BANK_AI_MODEL_ID", None) or getattr(
    settings, "OCR_MODEL_ID", "gemini-2.5-flash"
)
# Defaults used only when settings.AI_ROTATION_MODELS is empty.
_GEMINI_FALLBACKS = getattr(settings, "BANK_AI_GEMINI_FALLBACKS", None) or []
GROQ_MODEL_ID = getattr(settings, "GROQ_MODEL_ID", "llama-3.3-70b-versatile")
MAX_ROWS = 200
# Bank abbreviation is shown in a tight list cell (e.g. " /TD"); keep it short.
MAX_BANK_NAME_LEN = 6

# Transaction types Gemini may assign. Anything else collapses to "other".
BANK_TXN_TYPES = {"opening_balance", "invoice", "expense", "transfer", "other"}

_client: genai.Client | None = None
_groq_client: AsyncGroq | None = None


# ===========================================================================
# Model rotation (hard round-robin)
# ===========================================================================
# Every AI call takes the NEXT model from AI_MODELS and advances one shared,
# GLOBAL cursor -- so two consecutive calls, anywhere in the app, never hit the
# same model. There is NO in-call fallback and NO retry: a model that errors or
# returns nothing is already "spent", so the *next* call just uses the next model.
#
# To grow the rotation (to 3 or 30 models) edit settings.AI_ROTATION_MODELS --
# "provider:model_id" entries; nothing else changes. To support a new provider,
# add its key mapping below and a branch in _invoke().
_PROVIDER_KEYS = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}

_cursor = itertools.count()


def _parse_models(specs: list[str] | None) -> list[tuple[str, str]]:
    """Parse "provider:model_id" strings into (provider, model_id) pairs, skipping
    blanks and unknown providers."""
    models: list[tuple[str, str]] = []
    for spec in specs or []:
        provider, _, model_id = spec.partition(":")
        provider, model_id = provider.strip().lower(), model_id.strip()
        if provider in _PROVIDER_KEYS and model_id:
            models.append((provider, model_id))
    return models


# The rotation ring, from config (with a back-compat default if it's unset).
AI_MODELS: list[tuple[str, str]] = _parse_models(getattr(settings, "AI_ROTATION_MODELS", None)) or [
    ("groq", GROQ_MODEL_ID),
    ("gemini", BANK_AI_MODEL_ID),
    *[("gemini", m) for m in _GEMINI_FALLBACKS if m and m != BANK_AI_MODEL_ID],
]


def bank_ai_model_name() -> str:
    """The default/primary model name -- used only to label paths that make no AI
    call (e.g. an already-reconciled deposit). Live calls report the rotated model."""
    return BANK_AI_MODEL_ID


def _model_configured(provider: str) -> bool:
    attr = _PROVIDER_KEYS.get(provider)
    return bool(attr and getattr(settings, attr, ""))


def _usable_models() -> list[tuple[str, str]]:
    """The rotation ring limited to models whose provider has an API key set."""
    return [m for m in AI_MODELS if _model_configured(m[0])]


def next_ai_model() -> tuple[str, str]:
    """Hard-rotate: return the next (provider, model_id) and advance the GLOBAL
    cursor so the very next AI call -- anywhere in the app -- uses a different model.

    Call this exactly ONCE per AI invocation (the cursor advances whether or not the
    model then succeeds -- a spent model is not retried). Raises 503 if nothing is
    configured.
    """
    usable = _usable_models()
    if not usable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No AI model configured (set GEMINI_API_KEY and/or GROQ_API_KEY)",
        )
    return usable[next(_cursor) % len(usable)]


def _get_client() -> genai.Client:
    """Lazily build the Gemini client so import never fails without a key."""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GEMINI_API_KEY is not configured",
            )
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _get_groq_client() -> AsyncGroq | None:
    """Lazily build the Groq client. Returns None when no key is configured."""
    global _groq_client
    if not settings.GROQ_API_KEY:
        return None
    if _groq_client is None:
        _groq_client = AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=getattr(settings, "OPENAI_TIMEOUT_SEC", 30),
        )
    return _groq_client


async def _call_gemini(model: str, prompt: str, system_instruction: str) -> str:
    response = await _get_client().aio.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    return _strip_json_fences(response.text or "")


async def _call_groq(model: str, prompt: str, system_instruction: str) -> str:
    client = _get_groq_client()
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured")
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    if not response.choices:
        return ""
    return _strip_json_fences(response.choices[0].message.content or "")


async def _invoke(provider: str, model_id: str, prompt: str, system_instruction: str) -> str:
    """Call one model via its provider's client and return raw text output."""
    if provider == "gemini":
        return await _call_gemini(model_id, prompt, system_instruction)
    if provider == "groq":
        return await _call_groq(model_id, prompt, system_instruction)
    raise RuntimeError(f"Unknown AI provider: {provider}")


async def _generate_json(
    prompt: str, system_instruction: str, model: tuple[str, str] | None = None
) -> tuple[str, str]:
    """Invoke exactly ONE model and return (raw_json, model_id).

    Hard rotation: uses `model` if the caller already drew one (so a streaming caller
    can announce it first), else the next model from next_ai_model(). Either way the
    global cursor advances once. There is no retry and no in-call fallback -- if the
    model errors or returns nothing this returns ("", model_id) and the *next* call
    naturally uses the next model. The model_id is always returned so callers can
    report which model ran.
    """
    provider, model_id = model or next_ai_model()
    try:
        raw = await _invoke(provider, model_id, prompt, system_instruction)
    except Exception as exc:  # noqa: BLE001 - one shot; the next call rotates onward
        logger.warning("AI %s:%s failed: %s", provider, model_id, exc)
        raw = ""
    return raw, model_id


def _strip_json_fences(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


_SYSTEM_INSTRUCTION = (
    "You read raw bank statement text a person pasted or typed and return the "
    "transactions as strict JSON. The input may be tab/space/comma separated "
    "columns, or loose natural language — interpret it robustly.\n"
    "Return ONLY a JSON object of this shape:\n"
    '{ "transactions": [ { "type": "opening_balance|invoice|expense|transfer|other", '
    '"txn_date": "YYYY-MM-DD or null", "description": "merchant or memo", '
    '"debit": number-or-null, "credit": number-or-null, "balance": number-or-null, '
    '"bank_name": "short bank abbreviation or null" } ] }\n'
    "Rules:\n"
    "- bank_name: the SHORT, formal, well-known abbreviation of the bank the "
    "statement is from, derived from any bank name/header in the text (e.g. "
    '"TD Canada Trust" -> "TD", "Royal Bank of Canada" -> "RBC", '
    '"Bank of Montreal" -> "BMO", "Canadian Imperial Bank of Commerce" -> "CIBC", '
    '"Bank of Nova Scotia" -> "Scotia"). Max 6 characters, uppercase where '
    "conventional. Use the same value for every row of the same statement. If no "
    "bank is identifiable, use null.\n"
    "- debit = money OUT of the account (withdrawals, payments, transfers out). "
    "credit = money IN (deposits, incoming payments).\n"
    "- All amounts are positive numbers. Accounting negatives like (123.45) mean "
    "money out -> put the positive value in debit.\n"
    "- Strip currency symbols and thousands separators (9,000.00 -> 9000.00).\n"
    "- Use ISO date YYYY-MM-DD. If a row clearly has no date, use null. If a date "
    "omits the year, assume the most recent past occurrence relative to today.\n"
    "- One JSON row per transaction line. Skip header rows and blank lines.\n"
    "- balance is the running balance if the row shows one, else null.\n"
    "Classify each row's type:\n"
    "- opening_balance: a starting/brought-forward balance line (usually the first row).\n"
    "- invoice: money IN from a customer paying an invoice (deposits, wires in, client payments). credit only.\n"
    "- expense: money OUT to pay a bill/purchase (rent, supplies, fees, payroll). debit only.\n"
    "- transfer: moving money between the owner's own accounts (to savings, from checking). "
    "May be debit (out) OR credit (in); use both only if the line truly shows both legs.\n"
    "- other: anything that doesn't fit.\n"
    "- Return valid JSON only, no commentary, no code fences."
)


def _coerce_amount(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError):
        return None
    if amount == 0:
        return None
    return amount.copy_abs()


def _coerce_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _coerce_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in BANK_TXN_TYPES else "other"


def _coerce_bank_name(value: Any) -> str | None:
    """A short formal bank abbreviation, capped so it fits the list cell."""
    text = str(value or "").strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    return text[:MAX_BANK_NAME_LEN]


def _normalise_row(row: dict[str, Any]) -> dict[str, Any] | None:
    description = str(row.get("description") or "").strip() or "(no description)"
    txn_type = _coerce_type(row.get("type"))
    debit = _coerce_amount(row.get("debit"))
    credit = _coerce_amount(row.get("credit"))
    balance = _coerce_amount(row.get("balance"))
    # A row with neither debit nor credit carries no money movement — drop it,
    # unless it's an opening balance (which legitimately shows only a balance).
    if debit is None and credit is None:
        if txn_type == "opening_balance" and balance is not None:
            credit = balance
        else:
            return None
    # Only a transfer may legitimately carry both legs; for every other type a
    # both-sided row is a model slip — keep the larger side.
    if debit is not None and credit is not None and txn_type != "transfer":
        if credit >= debit:
            debit = None
        else:
            credit = None
    return {
        "type": txn_type,
        "txn_date": _coerce_date(row.get("txn_date")),
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "bank_name": _coerce_bank_name(row.get("bank_name")),
    }


async def interpret_bank_text(
    text: str, model: tuple[str, str] | None = None
) -> tuple[list[dict[str, Any]], str]:
    """Interpret pasted/typed bank text into normalised transaction rows.

    Returns (rows, model_used): rows are dicts with keys txn_date (date|None),
    description (str), debit/credit/balance (Decimal|None); model_used is the model
    that actually ran, for accurate reporting. `model` is an optional pre-drawn
    (provider, model_id) from next_ai_model() so a streaming caller can announce it
    before the call; omitted means draw the next model here. Raises HTTPException on
    bad input or when the model returns nothing (the user retries -> next model).
    """
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="text is required"
        )

    prompt = (
        f"Today is {datetime.now(timezone.utc).date().isoformat()}.\n"
        f"Default currency: {getattr(settings, 'DEFAULT_CURRENCY', 'CAD')}.\n\n"
        "Bank statement text to interpret:\n"
        "-----\n"
        f"{text.strip()}\n"
        "-----"
    )

    # Use this call's rotated model (one shot; no fallback here).
    raw, model_used = await _generate_json(prompt, _SYSTEM_INSTRUCTION, model)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{model_used} returned nothing — try again to use the next model",
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Bank AI returned invalid JSON"
        ) from exc

    transactions = parsed.get("transactions") if isinstance(parsed, dict) else None
    if not isinstance(transactions, list) or not transactions:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bank AI found no transactions in the text",
        )
    if len(transactions) > MAX_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many transactions in one paste (max {MAX_ROWS})",
        )

    rows: list[dict[str, Any]] = []
    for row in transactions:
        if not isinstance(row, dict):
            continue
        normalised = _normalise_row(row)
        if normalised is not None:
            rows.append(normalised)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned no usable transaction rows",
        )
    return rows, model_used


# ---------- AI reconcile suggestion ----------

_RECONCILE_SYSTEM_INSTRUCTION = (
    "You are a bookkeeping assistant reconciling ONE incoming bank deposit against "
    "a list of that business's outstanding customer invoices. Decide which "
    "invoice(s) this single deposit most likely paid.\n"
    "Return ONLY a JSON object of this shape:\n"
    '{ "matches": [ { "inv_id": "the candidate id", '
    '"confidence": 0.0-1.0, "reason": "one short sentence" } ] }\n'
    "How to reason (this is judgement, not a rigid rule):\n"
    "- AMOUNT is the strongest signal: a deposit usually equals one invoice's "
    "balance due, or the sum of a few invoices' balances. Prefer combinations whose "
    "balances add up to the deposit amount.\n"
    "- DATE: a deposit pays invoices that already existed, so an invoice dated on or "
    "before the deposit date (typically within ~90 days) is far more plausible than "
    "one dated AFTER the deposit — a deposit cannot pay an invoice issued later. "
    "Heavily penalise invoices dated after the deposit.\n"
    "- PAYER: if the deposit description names a company/person, prefer that client's "
    "invoices.\n"
    "- Only include invoices you actually believe were paid. Omit weak guesses "
    "rather than listing everything. If nothing is a credible match, return an empty "
    "matches array.\n"
    "- confidence reflects how sure you are (1.0 = near-certain exact amount+date+payer match).\n"
    "- Return valid JSON only, no commentary, no code fences."
)


async def suggest_invoice_matches(
    deposit: dict[str, Any], candidates: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    """Ask the AI which candidate invoices this deposit likely paid.

    Returns (matches, model_used): matches is a list of {inv_id: str, confidence:
    float, reason: str} restricted to the given candidates; model_used is the model
    that actually ran (post-rotation/fallback), for accurate reporting. Uses the same
    shared rotation as bank-text interpretation. Raises HTTPException only if every
    model fails; the caller should treat any failure as "no suggestion" and never
    block reconcile.
    """
    if not candidates:
        return [], bank_ai_model_name()

    valid_ids = {str(c.get("inv_id")) for c in candidates}
    invoice_lines = [
        {
            "inv_id": str(c.get("inv_id")),
            "inv_number": c.get("inv_number"),
            "inv_date": c["inv_date"].isoformat() if c.get("inv_date") else None,
            "client": c.get("client_company_name"),
            "total": str(c["inv_total"]) if c.get("inv_total") is not None else None,
            "balance_due": str(c["inv_balance_due"]) if c.get("inv_balance_due") is not None else None,
        }
        for c in candidates
    ]
    prompt = (
        f"Today is {datetime.now(timezone.utc).date().isoformat()}.\n"
        "DEPOSIT to reconcile:\n"
        f"{json.dumps(deposit, ensure_ascii=False, default=str)}\n\n"
        "OUTSTANDING INVOICE CANDIDATES (choose only from these inv_id values):\n"
        f"{json.dumps(invoice_lines, ensure_ascii=False)}"
    )

    raw, model_used = await _generate_json(prompt, _RECONCILE_SYSTEM_INSTRUCTION)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [], model_used

    matches = parsed.get("matches") if isinstance(parsed, dict) else None
    if not isinstance(matches, list):
        return [], model_used

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in matches:
        if not isinstance(m, dict):
            continue
        inv_id = str(m.get("inv_id") or "")
        if inv_id not in valid_ids or inv_id in seen:
            continue  # ignore hallucinated / duplicate ids
        seen.add(inv_id)
        try:
            confidence = max(0.0, min(1.0, float(m.get("confidence"))))
        except (TypeError, ValueError):
            confidence = 0.0
        reason = str(m.get("reason") or "").strip()[:200]
        out.append({"inv_id": inv_id, "confidence": confidence, "reason": reason})
    return out, model_used
