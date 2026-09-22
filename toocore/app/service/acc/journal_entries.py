from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Table, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.acc.ac_coa import COADB
from app.db.models.acc.ac_ledger import JournalEntryDB, JournalEntryLine
from app.schemas.sch_acc_je import JournalEntryOut, JournalEntryUpdateIn, JournalLineOut, NormalBalanceType
from app.schemas.sch_ai import JWType
from app.service.acc.accounting import is_period_closed, yyyymm_from_date
from app.service.acc.ai_drafting import generate_je_draft

JE_TABLE = cast(Table, JournalEntryDB.__table__)
JE_LINE_TABLE = cast(Table, JournalEntryLine.__table__)
COA_TABLE = cast(Table, COADB.__table__)
DBRow = Mapping[Any, Any]

_LINE_TYPES: set[str] = {"Debit", "Credit"}
_ROOT_BY_CODE = {
    "1000": "Asset",
    "2000": "Liability",
    "3000": "Equity",
    "4000": "Revenue",
    "5000": "Expense",
}


def _account_root(account: DBRow, accounts_by_id: Mapping[UUID, DBRow]) -> DBRow:
    current = account
    seen: set[UUID] = set()
    while current["parent_id"] and current["parent_id"] not in seen:
        seen.add(current["id"])
        parent = accounts_by_id.get(current["parent_id"])
        if parent is None:
            break
        current = parent
    return current


def _account_root_name(account: DBRow, accounts_by_id: Mapping[UUID, DBRow]) -> str | None:
    root = _account_root(account, accounts_by_id)
    return _ROOT_BY_CODE.get(root["coa_code"] or "", root["coa_name"])


async def _get_entry_or_404(
    conn: AsyncConnection,
    journal_entry_id: UUID,
    detail: str = "Journal entry not found",
) -> DBRow:
    entry = (
        await conn.execute(
            select(JE_TABLE)
            .where(JE_TABLE.c.id == journal_entry_id)
            .where(JE_TABLE.c.is_deleted.is_not(True))
        )
    ).mappings().one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return entry


async def create_ai_entry_for_transaction(
    txn: DBRow,
    zjwt: JWType,
    conn: AsyncConnection,
    force: bool = False,
) -> JournalEntryOut:
    existing_lines = list(
        (
            await conn.execute(
                select(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.journal_entry_id == txn["id"])
                .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    if existing_lines:
        if force:
            await conn.execute(
                update(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.journal_entry_id == txn["id"])
                .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
                .values(is_deleted=True)
            )
        else:
            return await entry_out(conn, txn)

    if txn["is_deleted"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction is void")

    amount = Decimal(txn["b_decimal"] or 0)
    if amount == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry transaction amount is required")

    period = yyyymm_from_date(txn["entry_date"])
    if await is_period_closed(conn, period):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Period is closed")

    all_accounts = list(
        (
            await conn.execute(
                select(COA_TABLE)
                .where(COA_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    accounts_by_id: dict[UUID, DBRow] = {account["id"]: account for account in all_accounts}
    accounts = [account for account in all_accounts if account["is_posting"] is True]
    if not accounts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No accounts available. Create accounts first.")

    ai_payload = generate_je_draft(
        amount=amount,
        description=txn["memo"] or txn["description"] or "",
        accounts=[
            {
                "id": str(a["id"]),
                "coa_code": a["coa_code"],
                "coa_name": a["coa_name"],
                "parent_id": str(a["parent_id"]) if a["parent_id"] else None,
                "root_name": _account_root_name(a, accounts_by_id),
                "coa_status": a["coa_status"],
                "coa_level": a["coa_level"],
                "normal_balance": a["normal_balance"],
            }
            for a in accounts
        ],
    )

    account_by_code = {a["coa_code"]: a for a in accounts}
    candidate_lines: list[tuple[UUID, str, Decimal, str | None]] = []
    for item in ai_payload.get("lines", []):
        account = account_by_code.get(str(item.get("coa_code", "")).strip())
        if not account:
            continue
        line_amount = Decimal(str(item.get("amount", "0")))
        line_type = str(item.get("line_type", ""))
        if line_amount <= 0 or line_type not in _LINE_TYPES:
            continue
        candidate_lines.append((account["id"], line_type, line_amount, item.get("note")))

    if not candidate_lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI did not produce valid journal lines")

    debit_total = sum((amount for _, line_type, amount, _ in candidate_lines if line_type == "Debit"), Decimal("0"))
    credit_total = sum((amount for _, line_type, amount, _ in candidate_lines if line_type == "Credit"), Decimal("0"))
    if debit_total != credit_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generated journal lines are not balanced")

    updated_txn = (
        await conn.execute(
            update(JE_TABLE)
            .where(JE_TABLE.c.id == txn["id"])
            .values(
                memo=str(ai_payload.get("memo", (txn["memo"] or txn["description"] or "")[:120])),
                source="ai",
                entry_status="posted",
                posted_by=zjwt.zuid,
                period_yyyymm=period,
            )
            .returning(*JE_TABLE.c)
        )
    ).mappings().one()

    for account_id, line_type, line_amount, note in candidate_lines:
        await conn.execute(
            insert(JE_LINE_TABLE).values(
                journal_entry_id=txn["id"],
                account_id=account_id,
                line_type=line_type,
                amount=line_amount,
                description=note,
                ten_id=zjwt.ztid,
                biz_id=zjwt.zbid,
                usr_id=zjwt.zuid,
                created_by=zjwt.zuid,
            )
        )

    return await entry_out(conn, updated_txn)


async def generate_entry_for_transaction(
    conn: AsyncConnection,
    zjwt: JWType,
    transaction_id: UUID,
    force: bool = False,
) -> JournalEntryOut:
    txn = await _get_entry_or_404(conn, transaction_id, detail="Transaction not found")
    return await create_ai_entry_for_transaction(txn=txn, zjwt=zjwt, conn=conn, force=force)


async def entry_out(conn: AsyncConnection, entry: DBRow) -> JournalEntryOut:
    line_rows = list(
        (
            await conn.execute(
                select(
                    JE_LINE_TABLE.c.id,
                    JE_LINE_TABLE.c.journal_entry_id,
                    JE_LINE_TABLE.c.account_id,
                    JE_LINE_TABLE.c.line_type,
                    JE_LINE_TABLE.c.amount,
                    JE_LINE_TABLE.c.description,
                    COA_TABLE.c.coa_code,
                    COA_TABLE.c.coa_name,
                    COA_TABLE.c.parent_id,
                    COA_TABLE.c.coa_status,
                    COA_TABLE.c.coa_level,
                )
                .join(COA_TABLE, COA_TABLE.c.id == JE_LINE_TABLE.c.account_id, isouter=True)
                .where(JE_LINE_TABLE.c.journal_entry_id == entry["id"])
                .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    lines = [
        JournalLineOut(
            id=line["id"],
            journal_entry_id=line["journal_entry_id"],
            account_id=line["account_id"],
            coa_code=line["coa_code"],
            coa_name=line["coa_name"],
            parent_id=line["parent_id"],
            coa_status=line["coa_status"],
            coa_level=line["coa_level"],
            line_type=cast(NormalBalanceType, line["line_type"] if line["line_type"] in _LINE_TYPES else "Debit"),
            amount=line["amount"],
            description=line["description"],
        )
        for line in line_rows
    ]
    return JournalEntryOut(
        id=entry["id"],
        entry_no=entry["entry_no"],
        entry_date=entry["entry_date"],
        memo=entry["memo"],
        source=entry["source"],
        entry_status=entry["entry_status"] or "Draft",
        period_yyyymm=entry["period_yyyymm"],
        posted_at=entry["posted_at"],
        is_reversal=entry["is_reversal"],
        lines=lines,
    )


async def list_journal_entries(
    conn: AsyncConnection,
    period_yyyymm: int | None = None,
    limit: int = 100,
) -> list[JournalEntryOut]:
    stmt = select(JE_TABLE).order_by(JE_TABLE.c.posted_at.desc())
    stmt = stmt.where(JE_TABLE.c.is_deleted.is_not(True))
    if period_yyyymm is not None:
        stmt = stmt.where(JE_TABLE.c.period_yyyymm == period_yyyymm)
    entries = list((await conn.execute(stmt.limit(limit))).mappings().all())
    return [await entry_out(conn, entry) for entry in entries]


async def get_journal_entry(conn: AsyncConnection, journal_entry_id: UUID) -> JournalEntryOut:
    entry = await _get_entry_or_404(conn, journal_entry_id)
    return await entry_out(conn, entry)


async def update_journal_entry(
    conn: AsyncConnection,
    zjwt: JWType,
    journal_entry_id: UUID,
    payload: JournalEntryUpdateIn,
) -> JournalEntryOut:
    entry = await _get_entry_or_404(conn, journal_entry_id)
    target_date = payload.entry_date or entry["entry_date"]
    period = yyyymm_from_date(target_date)
    if await is_period_closed(conn, period):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Period is closed")

    if not payload.lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry must have lines")

    payload_line_ids = [line.id for line in payload.lines if line.id is not None]
    if len(payload_line_ids) != len(set(payload_line_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate journal line id")

    account_ids = {line.account_id for line in payload.lines}
    accounts = list(
        (
            await conn.execute(
                select(COA_TABLE)
                .where(COA_TABLE.c.id.in_(account_ids))
                .where(COA_TABLE.c.is_deleted.is_not(True))
                .where(COA_TABLE.c.is_posting.is_(True))
            )
        ).mappings().all()
    )
    account_by_id = {account["id"]: account for account in accounts}
    missing_account_ids = account_ids - set(account_by_id)
    if missing_account_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal line account not found")

    debit_total = Decimal("0")
    credit_total = Decimal("0")
    for line in payload.lines:
        if line.amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal line amount must be greater than zero")
        if line.line_type == "Debit":
            debit_total += line.amount
        elif line.line_type == "Credit":
            credit_total += line.amount
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid line type")

    if debit_total <= 0 or credit_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry must include debit and credit lines")
    if debit_total != credit_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry is not balanced")

    existing_lines = list(
        (
            await conn.execute(
                select(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.journal_entry_id == entry["id"])
                .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    existing_by_id = {line["id"]: line for line in existing_lines}

    for line_id in payload_line_ids:
        if line_id not in existing_by_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal line does not belong to this entry")

    incoming_ids = set(payload_line_ids)
    for line in existing_lines:
        if line["id"] not in incoming_ids:
            await conn.execute(
                update(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.id == line["id"])
                .values(is_deleted=True)
            )

    for line_payload in payload.lines:
        values = {
            "account_id": line_payload.account_id,
            "line_type": line_payload.line_type,
            "amount": line_payload.amount,
            "description": line_payload.description,
        }
        if line_payload.id is not None:
            await conn.execute(
                update(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.id == line_payload.id)
                .values(**values)
            )
        else:
            await conn.execute(
                insert(JE_LINE_TABLE).values(
                    journal_entry_id=entry["id"],
                    ten_id=zjwt.ztid,
                    biz_id=zjwt.zbid,
                    usr_id=zjwt.zuid,
                    created_by=zjwt.zuid,
                    **values,
                )
            )

    updated_entry = (
        await conn.execute(
            update(JE_TABLE)
            .where(JE_TABLE.c.id == entry["id"])
            .values(entry_date=target_date, period_yyyymm=period, memo=payload.memo)
            .returning(*JE_TABLE.c)
        )
    ).mappings().one()
    return await entry_out(conn, updated_entry)


async def isdelete_journal_entry(conn: AsyncConnection, journal_entry_id: UUID) -> None:
    entry = await _get_entry_or_404(conn, journal_entry_id)
    if await is_period_closed(conn, entry["period_yyyymm"]):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Period is closed")

    await conn.execute(
        update(JE_TABLE)
        .where(JE_TABLE.c.id == entry["id"])
        .values(is_deleted=True)
    )
    await conn.execute(
        update(JE_LINE_TABLE)
        .where(JE_LINE_TABLE.c.journal_entry_id == entry["id"])
        .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
        .values(is_deleted=True)
    )


async def reverse_journal_entry(
    conn: AsyncConnection,
    zjwt: JWType,
    journal_entry_id: UUID,
) -> JournalEntryOut:
    original = (
        await conn.execute(
            select(JE_TABLE)
            .where(JE_TABLE.c.id == journal_entry_id)
        )
    ).mappings().one_or_none()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")

    original_lines = list(
        (
            await conn.execute(
                select(JE_LINE_TABLE)
                .where(JE_LINE_TABLE.c.journal_entry_id == original["id"])
            )
        ).mappings().all()
    )
    if not original_lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Journal entry has no lines")

    period = yyyymm_from_date(datetime.now(timezone.utc).date())
    if await is_period_closed(conn, period):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Current period is closed")

    reversal = (
        await conn.execute(
            insert(JE_TABLE)
            .values(
                ten_id=zjwt.ztid,
                biz_id=zjwt.zbid,
                usr_id=zjwt.zuid,
                created_by=zjwt.zuid,
                entry_date=datetime.now(timezone.utc).date(),
                memo=f"Reversal of entry {original['entry_no']}",
                source="reversal",
                entry_status="posted",
                source_ref_id=original["id"],
                posted_by=zjwt.zuid,
                period_yyyymm=period,
                is_reversal=True,
                reversed_entry_id=original["id"],
            )
            .returning(*JE_TABLE.c)
        )
    ).mappings().one()

    for line in original_lines:
        await conn.execute(
            insert(JE_LINE_TABLE).values(
                journal_entry_id=reversal["id"],
                account_id=line["account_id"],
                line_type="Credit" if line["line_type"] == "Debit" else "Debit",
                amount=Decimal(line["amount"]),
                description=f"Reversal: {line['description'] or ''}".strip(),
                ten_id=zjwt.ztid,
                biz_id=zjwt.zbid,
                usr_id=zjwt.zuid,
                created_by=zjwt.zuid,
            )
        )

    return await entry_out(conn, reversal)
