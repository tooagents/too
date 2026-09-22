import json
import logging
import os
import re
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAI

from app.config import get_settings_singleton

settings = get_settings_singleton()
logger = logging.getLogger("app.acc.ai")
OPENAI_ENABLED = getattr(settings, "OPENAI_ENABLED", True)
DEFAULT_CURRENCY = getattr(settings, "DEFAULT_CURRENCY", "CAD")
DEFAULT_TAX_JURISDICTION = getattr(settings, "DEFAULT_TAX_JURISDICTION", "CA")
OPENAI_TIMEOUT_SEC = getattr(settings, "OPENAI_TIMEOUT_SEC", 30)


def accounting_ai_model_name() -> str:
    return getattr(settings, "GH_OPENAI_MODEL_DEFAULT", "openai/gpt-4.1-mini")


def _extract_json_object(raw: str, *, provider_name: str = "GitHub Models") -> dict[str, Any]:
    cleaned = raw.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{provider_name} returned empty content")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{provider_name} returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{provider_name} JSON must be an object")
    return parsed


async def generate_accounting_json_async(prompt: dict[str, Any]) -> dict[str, Any]:
    api_key = settings.GH_OPENAI_API_KEY or os.environ.get("GH_OPENAI_API_KEY")

    # To reverse later, use the direct OpenAI key/model/client below:
    # api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    # model = getattr(settings, "OPENAI_MODEL_DEFAULT", "gpt-5-mini")
    # client = AsyncOpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT_SEC)
    # response = await client.responses.create(
    #     model=model,
    #     input=[{"role": "user", "content": [{"type": "input_text", "text": json.dumps(prompt)}]}],
    # )
    # return _extract_json_object((response.output_text or "").strip(), provider_name="OpenAI")

    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GH_OPENAI_API_KEY is not configured")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=getattr(settings, "GH_OPENAI_BASE_URL", "https://models.github.ai/inference"),
        timeout=OPENAI_TIMEOUT_SEC,
    )
    try:
        logger.info("calling GitHub Models accounting JSON model=%s", accounting_ai_model_name())
        response = await client.chat.completions.create(
            model=accounting_ai_model_name(),
            messages=[{"role": "user", "content": json.dumps(prompt)}],
        )
        logger.info("GitHub Models accounting JSON response received model=%s", accounting_ai_model_name())
    except Exception as exc:
        logger.exception("GitHub Models accounting JSON request failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub Models request failed: {exc}") from exc

    if not response.choices:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned no choices")
    return _extract_json_object((response.choices[0].message.content or "").strip())


def generate_accounting_json(prompt: dict[str, Any]) -> dict[str, Any]:
    api_key = settings.GH_OPENAI_API_KEY or os.environ.get("GH_OPENAI_API_KEY")

    # To reverse later, use the direct OpenAI key/model/client below:
    # api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    # model = getattr(settings, "OPENAI_MODEL_DEFAULT", "gpt-5-mini")
    # client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT_SEC)
    # response = client.responses.create(
    #     model=model,
    #     input=[{"role": "user", "content": [{"type": "input_text", "text": json.dumps(prompt)}]}],
    # )
    # return _extract_json_object((response.output_text or "").strip(), provider_name="OpenAI")

    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GH_OPENAI_API_KEY is not configured")

    client = OpenAI(
        api_key=api_key,
        base_url=getattr(settings, "GH_OPENAI_BASE_URL", "https://models.github.ai/inference"),
        timeout=OPENAI_TIMEOUT_SEC,
    )
    try:
        logger.info("calling GitHub Models accounting JSON model=%s", accounting_ai_model_name())
        response = client.chat.completions.create(
            model=accounting_ai_model_name(),
            messages=[{"role": "user", "content": json.dumps(prompt)}],
        )
        logger.info("GitHub Models accounting JSON response received model=%s", accounting_ai_model_name())
    except Exception as exc:
        logger.exception("GitHub Models accounting JSON request failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub Models request failed: {exc}") from exc

    if not response.choices:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned no choices")
    return _extract_json_object((response.choices[0].message.content or "").strip())


def _find_account_code(accounts: list[dict[str, Any]], root_name: str, default_index: int = 0) -> str:
    for account in accounts:
        if account.get("root_name") == root_name and account.get("coa_code"):
            return str(account["coa_code"])
    if accounts:
        return str(accounts[min(default_index, len(accounts) - 1)].get("coa_code") or "")
    return ""


def _fallback_draft(amount: Decimal, description: str, accounts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    accounts = accounts or []
    abs_amount = abs(amount)
    debit_coa_code = _find_account_code(accounts, "Expense" if amount < 0 else "Asset", 0)
    credit_coa_code = _find_account_code(accounts, "Asset" if amount < 0 else "Revenue", 1)
    return {
        "confidence": 0.62,
        "memo": description[:120],
        "rationale": "Fallback heuristic used because model output was unavailable or invalid.",
        "lines": [
            {"coa_code": debit_coa_code, "line_type": "Debit", "amount": float(abs_amount), "note": "Auto draft"},
            {"coa_code": credit_coa_code, "line_type": "Credit", "amount": float(abs_amount), "note": "Auto draft"},
        ],
    }


def generate_je_draft(*, amount: Decimal, description: str, accounts: list[dict[str, Any]]) -> dict[str, Any]:
    api_key = settings.GH_OPENAI_API_KEY or os.environ.get("GH_OPENAI_API_KEY")
    if not OPENAI_ENABLED or not api_key:
        return _fallback_draft(amount, description, accounts)

    prompt = {
        "task": "Create balanced accounting journal entry lines.",
        "currency": DEFAULT_CURRENCY,
        "jurisdiction": DEFAULT_TAX_JURISDICTION,
        "transaction": {"description": description, "amount": float(amount)},
        "chart_of_accounts": accounts,
        "output_schema": {
            "confidence": "0..1 float",
            "memo": "short memo",
            "rationale": "short explanation",
            "lines": [{"coa_code": "string", "line_type": "Debit|Credit", "amount": "positive float", "note": "string"}],
        },
        "rules": ["Must be balanced", "Use only provided coa_code values", "Return JSON only"],
    }

    try:
        parsed = generate_accounting_json(prompt)
        if not isinstance(parsed, dict) or "lines" not in parsed:
            return _fallback_draft(amount, description, accounts)
        return parsed
    except Exception:
        return _fallback_draft(amount, description, accounts)
