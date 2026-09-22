import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import get_settings_singleton
from app.db.models.acc.ac_ledger import JournalEntryDB
from app.schemas.sch_ai import JWType
from app.service.acc.accounting import yyyymm_from_date
from app.service.acc.ai_drafting import generate_accounting_json_async
from app.service.acc.journal_entries import create_ai_entry_for_transaction

JE_TABLE = JournalEntryDB.__table__

settings = get_settings_singleton()
DEFAULT_CURRENCY = getattr(settings, "DEFAULT_CURRENCY", "CAD")


@dataclass
class InboxImportResult:
    message: str
    imported_count: int
    duplicate_count: int
    transactions: list[Mapping[str, Any]]


def _txn_hash(txn_date: date, description: str, amount: Decimal, currency: str) -> str:
    raw = f"{txn_date.isoformat()}|{description.strip().lower()}|{amount}|{currency.upper()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_ai_transaction(row: dict[str, Any]) -> tuple[date, str, Decimal, str]:
    try:
        txn_date = date.fromisoformat(str(row.get("txn_date") or "").strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned an invalid txn_date") from exc

    description = str(row.get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned a transaction without description")

    try:
        amount = Decimal(str(row.get("amount", "")).strip())
    except InvalidOperation as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned an invalid amount") from exc

    currency = str(row.get("currency") or DEFAULT_CURRENCY).strip().upper()
    if len(currency) != 3:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned an invalid currency")
    return txn_date, description, amount, currency


async def _interpret_inbox_message(message: str) -> list[dict[str, Any]]:
    if not isinstance(message, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message must be a string")

    prompt = {
        "task": "Extract accounting transactions from a human message for insertion into journal_entries.",
        "today": datetime.now(timezone.utc).date().isoformat(),
        "default_currency": DEFAULT_CURRENCY,
        "message": message,
        "rules": [
            "Return JSON only.",
            "Return every distinct transaction mentioned in the message.",
            "Use today's date when the message says today or omits a date.",
            "Use ISO date format YYYY-MM-DD.",
            "Amounts should be decimal numbers. Preserve negative signs if the message clearly describes money out.",
            "Descriptions should be concise merchant or memo text.",
            "Use a 3-letter currency code.",
        ],
        "output_schema": {
            "transactions": [
                {
                    "txn_date": "YYYY-MM-DD",
                    "description": "merchant or memo",
                    "amount": "decimal number",
                    "currency": DEFAULT_CURRENCY,
                }
            ]
        },
    }
    parsed = await generate_accounting_json_async(prompt)
    transactions = parsed.get("transactions")
    if not isinstance(transactions, list) or not transactions:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned no transactions")
    if len(transactions) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many transactions in one inbox message")

    rows = [row for row in transactions if isinstance(row, dict)]
    if len(rows) != len(transactions):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub Models returned an invalid transaction row")
    return rows


async def add_transactions_from_inbox_message(
    *,
    conn: AsyncConnection,
    zjwt: JWType,
    message: str,
) -> InboxImportResult:
    if not zjwt.ztid: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tenant id in JWT")

    parsed_rows = await _interpret_inbox_message(message)
    imported: list[JournalEntryDB] = []
    duplicate_count = 0

    for row in parsed_rows:
        txn_date, description, amount, currency = _parse_ai_transaction(row)
        hash_value = _txn_hash(txn_date, description, amount, currency)
        exists = await conn.execute(
            select(JE_TABLE.c.id).where(
                JE_TABLE.c.ten_id == zjwt.ztid,
                JE_TABLE.c.b_str == hash_value,
                JE_TABLE.c.is_deleted.is_not(True),
            )
        )
        if exists.first():
            duplicate_count += 1
            continue

        txn = (
            await conn.execute(
                insert(JE_TABLE)
                .values(
                    ten_id=zjwt.ztid,
                    biz_id=zjwt.zbid,
                    usr_id=zjwt.zuid,
                    created_by=zjwt.zuid,
                    entry_date=txn_date,
                    memo=description,
                    source="import",
                    source_ref_id=uuid4(),
                    entry_status="draft",
                    posted_by=zjwt.zuid,
                    period_yyyymm=yyyymm_from_date(txn_date),
                    b_str=hash_value,
                    b_decimal=amount,
                    locale=currency,
                    description=description,
                    extra={
                        "source_file_name": "api:add2inbox",
                        "external_id": f"api:{uuid4()}",
                        "transaction_hash": hash_value,
                        "transaction_amount": str(amount),
                        "currency": currency,
                    },
                )
                .returning(*JE_TABLE.c)
            )
        ).mappings().one()
        await create_ai_entry_for_transaction(txn=txn, zjwt=zjwt, conn=conn, force=False)
        imported.append(txn)

    return InboxImportResult(
        message=message,
        imported_count=len(imported),
        duplicate_count=duplicate_count,
        transactions=imported,
    )
