import csv
import io
import zipfile
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.acc.ac_coa import COADB
from app.db.models.acc.ac_ledger import JournalEntryDB, JournalEntryLine, PeriodCloseDB

COA_TABLE = COADB.__table__
JE_TABLE = JournalEntryDB.__table__
JE_LINE_TABLE = JournalEntryLine.__table__
PERIOD_CLOSE_TABLE = PeriodCloseDB.__table__


_DEFAULT_NORMAL_BALANCE = {
    "Asset": "Debit",
    "Expense": "Debit",
    "Liability": "Credit",
    "Equity": "Credit",
    "Revenue": "Credit",
}

_ROOT_BY_CODE = {
    "1000": "Asset",
    "2000": "Liability",
    "3000": "Equity",
    "4000": "Revenue",
    "5000": "Expense",
}


def yyyymm_from_date(d: date) -> int:
    return d.year * 100 + d.month


async def is_period_closed(conn: AsyncConnection, period_yyyymm: int) -> bool:
    row = (
        await conn.execute(
            select(PERIOD_CLOSE_TABLE.c.id)
            .where(PERIOD_CLOSE_TABLE.c.period_yyyymm == period_yyyymm)
            .where(PERIOD_CLOSE_TABLE.c.is_closed.is_(True))
        )
    ).first()
    return row is not None


async def ledger_rows(conn: AsyncConnection, from_date: date | None = None, to_date: date | None = None, account_id: UUID | None = None):
    stmt = (
        select(
            JE_TABLE.c.id,
            JE_TABLE.c.entry_date,
            JE_TABLE.c.memo,
            JE_LINE_TABLE.c.id,
            COA_TABLE.c.id,
            COA_TABLE.c.coa_code,
            COA_TABLE.c.coa_name,
            COA_TABLE.c.parent_id,
            COA_TABLE.c.coa_status,
            COA_TABLE.c.coa_level,
            COA_TABLE.c.normal_balance,
            COA_TABLE.c.is_posting,
            JE_LINE_TABLE.c.line_type,
            JE_LINE_TABLE.c.amount,
        )
        .join(JE_LINE_TABLE, JE_TABLE.c.id == JE_LINE_TABLE.c.journal_entry_id)
        .join(COA_TABLE, COA_TABLE.c.id == JE_LINE_TABLE.c.account_id)
        .where(JE_TABLE.c.is_deleted.is_not(True))
        .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
        .order_by(JE_TABLE.c.entry_date.asc(), JE_TABLE.c.posted_at.asc())
    )
    if from_date:
        stmt = stmt.where(JE_TABLE.c.entry_date >= from_date)
    if to_date:
        stmt = stmt.where(JE_TABLE.c.entry_date <= to_date)
    if account_id:
        stmt = stmt.where(COA_TABLE.c.id == account_id)
    return (await conn.execute(stmt)).all()


def _root_account(account_id: UUID, accounts_by_id: dict[UUID, Mapping[str, Any]]) -> Mapping[str, Any] | None:
    account = accounts_by_id.get(account_id)
    seen: set[UUID] = set()
    while account and account["parent_id"] and account["parent_id"] not in seen:
        seen.add(account["id"])
        parent = accounts_by_id.get(account["parent_id"])
        if parent is None:
            break
        account = parent
    return account


def _root_name(root: Mapping[str, Any] | None) -> str | None:
    if root is None:
        return None
    return _ROOT_BY_CODE.get(root["coa_code"] or "", root["coa_name"])


def account_signed_amount(root_name: str | None, normal_balance: str | None, line_type: str, amount: Decimal) -> Decimal:
    normal = normal_balance or _DEFAULT_NORMAL_BALANCE.get(root_name or "", "Debit")
    debit_positive = normal == "Debit"
    if debit_positive:
        return amount if line_type == "Debit" else -amount
    return -amount if line_type == "Debit" else amount


async def trial_balance(conn: AsyncConnection, from_date: date | None = None, to_date: date | None = None) -> list[dict]:
    account_rows = list(
        (
            await conn.execute(
                select(COA_TABLE)
                .where(COA_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    accounts_by_id = {account["id"]: account for account in account_rows}
    totals: dict[UUID, dict] = {}
    for row in await ledger_rows(conn, from_date=from_date, to_date=to_date):
        (
            _entry_id,
            _entry_date,
            _memo,
            _line_id,
            account_id,
            coa_code,
            coa_name,
            parent_id,
            coa_status,
            coa_level,
            normal_balance,
            is_posting,
            line_type,
            amount,
        ) = row
        if is_posting is not True:
            continue
        root_name = _root_name(_root_account(account_id, accounts_by_id))
        if account_id not in totals:
            totals[account_id] = {
                "account_id": account_id,
                "coa_code": coa_code,
                "coa_name": coa_name,
                "parent_id": root_name,
                "coa_status": coa_status,
                "coa_level": coa_level,
                "normal_balance": normal_balance,
                "debit": Decimal("0"),
                "credit": Decimal("0"),
                "balance": Decimal("0"),
            }
        if line_type == "Debit":
            totals[account_id]["debit"] += amount
        else:
            totals[account_id]["credit"] += amount
        totals[account_id]["balance"] += account_signed_amount(
            root_name,
            normal_balance,
            line_type,
            amount,
        )
    return list(totals.values())


def _posting_row(row: dict, amount: Decimal) -> dict:
    return {
        "account_id": row["account_id"],
        "coa_code": row["coa_code"],
        "coa_name": row["coa_name"],
        "parent_id": row["parent_id"],
        "coa_status": row["coa_status"],
        "coa_level": row["coa_level"],
        "amount": amount,
    }


def _new_level2(name: str | None) -> dict:
    return {"coa_status": name, "amount": Decimal("0"), "level3": []}


def _new_level3(name: str | None) -> dict:
    return {"coa_level": name, "amount": Decimal("0"), "posting_accounts": []}


def _add_to_section(section: dict, row: dict, amount: Decimal) -> None:
    section["amount"] += amount
    level2 = next(
        (item for item in section["level2"] if item["coa_status"] == row["coa_status"]),
        None,
    )
    if level2 is None:
        level2 = _new_level2(row["coa_status"])
        section["level2"].append(level2)
    level2["amount"] += amount

    level3 = next(
        (item for item in level2["level3"] if item["coa_level"] == row["coa_level"]),
        None,
    )
    if level3 is None:
        level3 = _new_level3(row["coa_level"])
        level2["level3"].append(level3)
    level3["amount"] += amount
    level3["posting_accounts"].append(_posting_row(row, amount))


def _report_sections(rows: list[dict], allowed_level1: list[str]) -> dict[str, dict]:
    sections = {
        level1.lower(): {"parent_id": level1, "amount": Decimal("0"), "level2": []}
        for level1 in allowed_level1
    }
    for row in rows:
        level1 = str(row["parent_id"] or "").lower()
        if level1 not in sections:
            continue
        amount = row["balance"]
        if amount == 0:
            continue
        _add_to_section(sections[level1], row, amount)
    return sections


async def balance_sheet(conn: AsyncConnection, as_of: date) -> dict:
    sections = _report_sections(await trial_balance(conn, to_date=as_of), ["Asset", "Liability", "Equity"])
    return {
        "as_of": as_of,
        "sections": sections,
        "totals": {
            "asset": sections["asset"]["amount"],
            "liability": sections["liability"]["amount"],
            "equity": sections["equity"]["amount"],
        },
    }


async def income_statement(conn: AsyncConnection, from_date: date, to_date: date) -> dict:
    sections = _report_sections(await trial_balance(conn, from_date=from_date, to_date=to_date), ["Revenue", "Expense"])
    net_income = sections["revenue"]["amount"] - sections["expense"]["amount"]
    return {
        "from_date": from_date,
        "to_date": to_date,
        "sections": sections,
        "totals": {
            "revenue": sections["revenue"]["amount"],
            "expense": sections["expense"]["amount"],
            "net_income": net_income,
        },
    }


def _flatten_section(section: dict) -> list[dict]:
    rows = []
    for level2 in section["level2"]:
        for level3 in level2["level3"]:
            rows.append(
                {
                    "parent_id": section["parent_id"],
                    "coa_status": level2["coa_status"],
                    "coa_level": level3["coa_level"],
                    "amount": level3["amount"],
                }
            )
    return rows


async def export_tax_package_zip(conn: AsyncConnection, period_yyyymm: int) -> bytes:
    year = period_yyyymm // 100
    month = period_yyyymm % 100
    from_date = date(year, month, 1)
    to_date = date(year, month, 28)
    # Keep month-end portable without external libs.
    while True:
        try:
            to_date = to_date.replace(day=to_date.day + 1)
        except ValueError:
            break

    tb = await trial_balance(conn, from_date=from_date, to_date=to_date)
    bs = await balance_sheet(conn, as_of=to_date)
    is_data = await income_statement(conn, from_date=from_date, to_date=to_date)

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, rows in [
            ("trial_balance.csv", tb),
            ("balance_sheet_asset.csv", _flatten_section(bs["sections"]["asset"])),
            ("balance_sheet_liability.csv", _flatten_section(bs["sections"]["liability"])),
            ("balance_sheet_equity.csv", _flatten_section(bs["sections"]["equity"])),
            ("income_statement_revenue.csv", _flatten_section(is_data["sections"]["revenue"])),
            ("income_statement_expense.csv", _flatten_section(is_data["sections"]["expense"])),
        ]:
            if not rows:
                zf.writestr(name, "")
                continue
            fieldnames = list(rows[0].keys())
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            zf.writestr(name, buf.getvalue())
    return out.getvalue()
