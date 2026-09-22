from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings_singleton
from app.db.models.acc.ac_coa import COADB
from app.db.models.db_schemas import SCHEMA_TOO_ACC
from app.schemas.sch_ai import JWType

settings = get_settings_singleton()
_ROOT_BY_CODE = {
    "1000": "Asset",
    "2000": "Liability",
    "3000": "Equity",
    "4000": "Revenue",
    "5000": "Expense",
}

_ALLOWED_INSERT_PREFIXES = (
    f"insert into {SCHEMA_TOO_ACC}.journal_entries",
    f"insert into {SCHEMA_TOO_ACC}.journal_entry_lines",
)
_ALLOWED_INSERT_COLUMNS = {
    f"{SCHEMA_TOO_ACC}.journal_entries": {
        "id",
        "ten_id",
        "biz_id",
        "usr_id",
        "created_by",
        "entry_date",
        "entry_status",
        "memo",
        "source",
        "source_ref_id",
        "posted_by",
        "posted_at",
        "period_yyyymm",
        "is_reversal",
        "b_decimal",
        "b_str",
        "description",
        "extra",
        "locale",
    },
    f"{SCHEMA_TOO_ACC}.journal_entry_lines": {
        "id",
        "ten_id",
        "biz_id",
        "usr_id",
        "created_by",
        "journal_entry_id",
        "account_id",
        "line_type",
        "amount",
        "description",
    },
}
_PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")
_INSERT_COLUMNS_RE = re.compile(
    rf"insert\s+into\s+({SCHEMA_TOO_ACC}\.(?:journal_entries|journal_entry_lines))\s*\(([^)]+)\)",
    flags=re.IGNORECASE,
)


def _extract_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI JSON must be an object")
    return parsed


def _normalize_sql(sql: str) -> str:
    normalized = sql.strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()
    if ";" in normalized or "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated SQL contains forbidden syntax")
    lowered = " ".join(normalized.lower().split())
    if not lowered.startswith(_ALLOWED_INSERT_PREFIXES):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated SQL targets an unsupported table")
    match = _INSERT_COLUMNS_RE.match(lowered)
    if not match:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated SQL must include an explicit column list")
    table_name = match.group(1)
    columns = {column.strip() for column in match.group(2).split(",")}
    unsupported = sorted(columns - _ALLOWED_INSERT_COLUMNS[table_name])
    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generated SQL uses unsupported columns: {', '.join(unsupported)}",
        )
    return normalized


def _validate_statement_params(sql: str, params: dict[str, Any]) -> None:
    missing = sorted(set(_PARAM_RE.findall(sql)) - set(params))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generated SQL is missing params: {', '.join(missing)}",
        )


def _validate_balanced_lines(lines: list[dict[str, Any]], valid_account_ids: set[str]) -> None:
    if len(lines) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry needs at least two lines")

    debit_total = Decimal("0")
    credit_total = Decimal("0")
    for line in lines:
        account_id = str(line.get("account_id", "")).strip()
        if account_id not in valid_account_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated journal line used an unknown account")
        line_type = str(line.get("line_type", "")).strip()
        if line_type not in {"Debit", "Credit"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated journal line has invalid line_type")
        try:
            amount = Decimal(str(line.get("amount", "0")))
        except InvalidOperation as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated journal line has invalid amount") from exc
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated journal line amount must be positive")
        if line_type == "Debit":
            debit_total += amount
        else:
            credit_total += amount

    if debit_total != credit_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated journal lines are not balanced")


def _default_server_params(zjwt: JWType, message: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    params = {
        "journal_entry_id": str(uuid4()),
        "ten_id": str(zjwt.ztid),
        "biz_id": str(zjwt.zbid) if zjwt.zbid else None,
        "usr_id": str(zjwt.zuid) if zjwt.zuid else None,
        "created_by": str(zjwt.zuid) if zjwt.zuid else None,
        "posted_by": str(zjwt.zuid) if zjwt.zuid else None,
        "source_ref_id": None,
        "source_file_name": "mcp:transaction2je",
        "external_id": str(uuid4()),
        "raw_message": message,
        "created_at": now.isoformat(),
        "posted_at": now.isoformat(),
    }
    for index in range(1, 7):
        params[f"journal_entry_line_{index}_id"] = str(uuid4())
    return params


def _account_root(account: COADB, accounts_by_id: dict[Any, COADB]) -> COADB:
    current = account
    seen: set[Any] = set()
    while current.parent_id and current.parent_id not in seen:
        seen.add(current.id)
        parent = accounts_by_id.get(current.parent_id)
        if parent is None:
            break
        current = parent
    return current


def _account_root_name(account: COADB, accounts_by_id: dict[Any, COADB]) -> str | None:
    root = _account_root(account, accounts_by_id)
    return _ROOT_BY_CODE.get(root.coa_code or "", root.coa_name)


async def _generate_transaction_sql(
    *,
    message: str,
    zjwt: JWType,
    accounts: list[COADB],
    all_accounts: list[COADB],
) -> dict[str, Any]:
    api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OPENAI_API_KEY is not configured")

    server_params = _default_server_params(zjwt, message)
    accounts_by_id = {account.id: account for account in all_accounts}
    prompt = {
        "task": "Convert a human-language transaction message into PostgreSQL INSERT statements for a journal entry.",
        "today": datetime.now(timezone.utc).date().isoformat(),
        "schema": SCHEMA_TOO_ACC,
        "message": message,
        "server_params": server_params,
        "tables": {table: sorted(columns) for table, columns in _ALLOWED_INSERT_COLUMNS.items()},
        "rules": [
            "Return JSON only.",
            "Generate INSERT statements only.",
            f"Allowed tables: {SCHEMA_TOO_ACC}.journal_entries, {SCHEMA_TOO_ACC}.journal_entry_lines.",
            "Use named SQLAlchemy parameters like :journal_entry_id and put values in params.",
            "Use the provided server_params for all id, tenant, business, user, created_by, posted_by, created_at, posted_at values.",
            "journal_entries.id must be :journal_entry_id, source must be 'ai', and entry_status must be 'posted'.",
            "Store the signed transaction amount on journal_entries.b_decimal and the currency on journal_entries.locale.",
            "period_yyyymm must match the transaction date.",
            "Journal lines must be balanced and must use only account_id values from chart_of_accounts.",
            "Only use chart_of_accounts rows where is_posting is true.",
            "Use between 2 and 6 journal lines. Use journal_entry_line_1_id through journal_entry_line_6_id for line ids.",
        ],
        "chart_of_accounts": [
            {
                "id": str(account.id),
                "coa_code": account.coa_code,
                "coa_name": account.coa_name,
                "parent_id": str(account.parent_id) if account.parent_id else None,
                "root_name": _account_root_name(account, accounts_by_id),
                "coa_status": account.coa_status,
                "coa_level": account.coa_level,
                "normal_balance": account.normal_balance,
                "is_posting": account.is_posting,
            }
            for account in accounts
        ],
        "output_schema": {
            "transaction": {
                "txn_date": "YYYY-MM-DD",
                "description": "merchant/description",
                "amount": "decimal number",
                "currency": "3-letter currency, default CAD if unspecified",
                "period_yyyymm": "integer",
            },
            "journal_lines": [
                {
                    "line_id_param": "parameter name used for this line id",
                    "account_id": "uuid from chart_of_accounts",
                    "line_type": "Debit|Credit",
                    "amount": "positive decimal",
                    "description": "short line memo",
                }
            ],
            "statements": [
                {
                    "sql": "INSERT INTO ... VALUES (:param, ...)",
                    "params": {"param": "value"},
                }
            ],
        },
    }

    model = getattr(settings, "OPENAI_MODEL_DEFAULT", "gpt-5-mini")
    client = OpenAI(api_key=api_key, timeout=getattr(settings, "OPENAI_TIMEOUT_SEC", 30))
    try:
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "input_text", "text": json.dumps(prompt)}]}],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OpenAI request failed: {exc}") from exc

    generated = _extract_json_object((response.output_text or "").strip())
    generated["_server_params"] = server_params
    return generated


async def create_transaction_and_journal_from_message(
    *,
    db: AsyncSession,
    zjwt: JWType,
    message: str,
) -> dict[str, object]:
    all_accounts = list((await db.execute(
        select(COADB)
        .where(COADB.is_deleted.is_not(True))
    )).scalars().all())
    accounts = [account for account in all_accounts if account.is_posting is True]
    if not accounts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No accounts available. Create accounts first.")

    generated = await _generate_transaction_sql(message=message, zjwt=zjwt, accounts=accounts, all_accounts=all_accounts)
    transaction = generated.get("transaction")
    journal_lines = generated.get("journal_lines")
    statements = generated.get("statements")
    if not isinstance(transaction, dict) or not isinstance(journal_lines, list) or not isinstance(statements, list):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OpenAI output is missing required sections")

    _validate_balanced_lines(
        [line for line in journal_lines if isinstance(line, dict)],
        {str(account.id) for account in accounts},
    )

    server_params = generated["_server_params"]
    executed = 0
    for statement in statements:
        if not isinstance(statement, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated statement must be an object")
        sql = _normalize_sql(str(statement.get("sql", "")))
        params = statement.get("params", {})
        if not isinstance(params, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated statement params must be an object")
        merged_params = {**params, **server_params}
        _validate_statement_params(sql, merged_params)
        await db.execute(text(sql), merged_params)
        executed += 1

    await db.commit()
    return {
        "message": message,
        "transaction_id": server_params["journal_entry_id"],
        "journal_entry_id": server_params["journal_entry_id"],
        "transaction": transaction,
        "journal_lines": journal_lines,
        "statement_count": executed,
    }
