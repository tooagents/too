from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.acc.o_bank_txn import OBankTxn
from app.db.repo.repo_inv import (
    clear_invoice_reconciliation_for_bank_txn,
    get_invoice_by_id,
    invoice_ids_reconciled_to,
    list_invoices,
    set_invoice_reconciliation,
)
from app.db.repo.repo_inv_payment import delete_invoice_payment
from app.db.repo.repo_o_bank_txn import (
    applied_totals_by_bank_txn,
    create_bank_txn,
    get_bank_txn_by_id,
    list_bank_txns,
    payments_for_bank_txn,
    soft_delete_bank_txn,
    update_bank_txn_fields,
)
from app.schemas.sch_ai import JWType
from app.service.acc.o_bank_ai import bank_ai_model_name, suggest_invoice_matches
from app.service.ser_inv import create_inv_payment, recalculate_invoice_payment_summary


def _base_ids(zjwt: JWType) -> dict[str, UUID | None]:
    return {
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zuid,
        "usr_id": zjwt.zuid,
        "cli_id": zjwt.zuid,
        "created_by": zjwt.zuid,
    }


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# ---------- bank txn CRUD ----------

async def fetch_bank_txns(zjwt: JWType, db: AsyncConnection) -> list[dict]:
    """List deposits/debits with applied/unapplied derived on read."""
    txns = await list_bank_txns(db)
    ids = [t.id for t in txns]
    applied = await applied_totals_by_bank_txn(db, ids)
    inv_map = await invoice_ids_reconciled_to(db, ids)
    return [_to_view(t, applied, inv_map) for t in txns]


def _to_view(
    txn: OBankTxn,
    applied: dict[UUID, Decimal],
    inv_map: dict[UUID, list[UUID]],
) -> dict:
    applied_total = applied.get(txn.id, Decimal("0"))
    credit = _to_decimal(txn.credit)
    unapplied = credit - applied_total
    if unapplied < Decimal("0"):
        unapplied = Decimal("0")
    return {
        "id": txn.id,
        "txn_date": txn.txn_date,
        "description": txn.description,
        "debit": txn.debit,
        "credit": txn.credit,
        "balance": txn.balance,
        "source": txn.source,
        "status": txn.status,
        "bank_name": txn.bank_name,
        "type": txn.type,
        "note": txn.note,
        "is_reconciled": bool(txn.is_reconciled),
        "applied_total": applied_total,
        "unapplied": unapplied,
        "paid_inv_ids": inv_map.get(txn.id, []),
        "created_at": txn.created_at,
    }


async def create_or_update_bank_txn(zjwt: JWType, db: AsyncConnection, payload: dict) -> dict:
    data = dict(payload)
    txn_id = data.pop("id", None)
    if txn_id:
        existing = await get_bank_txn_by_id(db, txn_id)
        if existing:
            updates = {k: v for k, v in data.items() if k not in _base_ids(zjwt)}
            txn = await update_bank_txn_fields(db, existing, updates)
            return _to_view(txn, {}, {})
    create_payload = {**_base_ids(zjwt), **data}
    if not create_payload.get("source"):
        create_payload["source"] = "manual"
    txn = await create_bank_txn(db, create_payload)
    return _to_view(txn, {}, {})


async def delete_bank_txn(zjwt: JWType, db: AsyncConnection, bank_txn_id: UUID) -> None:
    """Soft-delete a deposit/debit and release any invoice payments it linked.

    Clearing the bank-linked payments (like reconcile does) lets each touched
    invoice's paid-status recalculate, so deleting a reconciled deposit unpays
    its invoices instead of stranding them.
    """
    txn = await get_bank_txn_by_id(db, bank_txn_id)
    if not txn:
        raise ValueError("Bank transaction not found")

    touched: set[UUID] = set()
    # Clear the invoice-level reconcile links (the source of truth) ...
    touched.update(await clear_invoice_reconciliation_for_bank_txn(db, bank_txn_id))
    # ... and release the side-work payments so paid-status recalculates.
    existing = await payments_for_bank_txn(db, bank_txn_id)
    for payment in existing:
        touched.add(payment.inv_id)
        await delete_invoice_payment(db, payment)

    await soft_delete_bank_txn(db, txn)

    for inv_id in touched:
        await recalculate_invoice_payment_summary(db, inv_id)


# ---------- reconcile ----------

# Statuses that make an invoice un-matchable regardless of reconcile state — the
# document no longer represents money to collect (voided/cancelled/refunded). NOTE:
# 'paid' is deliberately NOT here: reconciliation is a separate axis from payment, so
# a paid-but-unreconciled invoice must still be a candidate ("the deposit that paid it
# just hasn't been linked yet"). A denylist, not an allowlist, because the stored
# inv_payment_status is inconsistent in casing/wording.
_UNMATCHABLE_STATUSES = {
    "void", "voided", "cancelled", "canceled",
    "refunded", "written off", "writeoff", "write-off",
}


async def _reconcile_candidates(db: AsyncConnection, this_txn_id: UUID) -> list[dict]:
    """Invoices offered for THIS deposit. Candidacy is the reconcile axis, not payment:
    anything not yet reconciled (paid, partial or unpaid), plus whatever is already
    reconciled to THIS deposit (so the panel can show + un-tick it). Invoices reconciled
    to a *different* deposit, and void/cancelled ones, are excluded."""
    invoices = await list_invoices(db)
    candidates = []
    for inv in invoices:
        status = (inv.inv_payment_status or "").strip().lower()
        if status in _UNMATCHABLE_STATUSES:
            continue
        linked_here = inv.reconciled_bank_txn_id == this_txn_id
        if inv.is_reconciled and not linked_here:
            continue  # reconciled to another deposit — not available
        candidates.append(
            {
                "inv_id": inv.id,
                "inv_number": inv.inv_number,
                "inv_date": inv.inv_date,
                "client_company_name": inv.client_company_name,
                "inv_total": inv.inv_total,
                "inv_balance_due": inv.inv_balance_due,
            }
        )
    # Oldest invoice first (FIFO, the AR convention: clear the oldest debt first),
    # undated invoices last. This is display order only, not match ranking.
    candidates.sort(key=lambda c: (c["inv_date"] is None, c["inv_date"] if c["inv_date"] is not None else 0))
    return candidates


async def build_reconcile_view(zjwt: JWType, db: AsyncConnection, bank_txn_id: UUID) -> dict:
    """The deposit plus the candidate invoices for it."""
    txn = await get_bank_txn_by_id(db, bank_txn_id)
    if not txn:
        raise ValueError("Bank transaction not found")

    applied = await applied_totals_by_bank_txn(db, [txn.id])
    inv_map = await invoice_ids_reconciled_to(db, [txn.id])
    bank_view = _to_view(txn, applied, inv_map)

    candidates = await _reconcile_candidates(db, txn.id)
    return {"bank_txn": bank_view, "candidates": candidates}


async def suggest_reconcile_matches(
    zjwt: JWType, db: AsyncConnection, bank_txn_id: UUID
) -> dict:
    """AI suggestion of which outstanding invoices this deposit likely paid.

    Best-effort: any AI/provider failure yields an empty suggestion list rather
    than an error, so the reconcile panel never breaks on a bad AI call.
    """
    txn = await get_bank_txn_by_id(db, bank_txn_id)
    if not txn:
        raise ValueError("Bank transaction not found")

    inv_map = await invoice_ids_reconciled_to(db, [txn.id])
    linked_here = set(inv_map.get(txn.id, []))

    # Already reconciled -> nothing to suggest; don't spend an AI call redoing it.
    if linked_here:
        return {"suggestions": [], "model": bank_ai_model_name()}

    candidates = await _reconcile_candidates(db, txn.id)

    credit = _to_decimal(txn.credit)
    # Only deposits (money in) with candidates are worth an AI reconcile pass.
    if credit <= Decimal("0") or not candidates:
        return {"suggestions": [], "model": bank_ai_model_name()}

    deposit = {
        "txn_date": txn.txn_date.isoformat() if txn.txn_date else None,
        "amount": str(credit),
        "description": txn.description,
        "bank_name": txn.bank_name,
    }
    try:
        suggestions, model_used = await suggest_invoice_matches(deposit, candidates)
    except Exception:  # noqa: BLE001 - AI is advisory; never block reconcile
        suggestions, model_used = [], bank_ai_model_name()
    return {"suggestions": suggestions, "model": model_used}


def _inv_sort_key(inv) -> tuple:
    """FIFO: oldest issue-date first, undated last (mirrors candidate display order)."""
    return (inv.inv_date is None, inv.inv_date if inv.inv_date is not None else 0)


async def reconcile_deposit(
    zjwt: JWType, db: AsyncConnection, bank_txn_id: UUID, inv_ids: list[UUID]
) -> dict:
    """Reconcile a deposit to the matched invoices. Reconciliation is a MATCH:

    Layer 1 (truth): the bank_txn <-> invoice link + is_reconciled flags, set here
    explicitly. This is the reconciliation record.
    Layer 2 (side-work, backend-owned): the deposit amount is recorded as payment(s)
    against the matched invoices, then the existing payment logic
    (recalculate_invoice_payment_summary) derives paid/partial status. The client sends
    only the matched invoice ids — never amounts. The deposit is spread across the
    matched invoices FIFO: each takes what it still owes (an already-paid invoice takes
    its full total, so a "just match" still records the deposit as its payment); any
    remainder beyond the matched invoices' need stays unapplied.

    Passing no ids de-reconciles the deposit (clears links + flags + payments).
    """
    txn = await get_bank_txn_by_id(db, bank_txn_id)
    if not txn:
        raise ValueError("Bank transaction not found")

    touched: set[UUID] = set()

    # 1. Clear this deposit's prior state: invoice links (truth) + side-work payments.
    touched.update(await clear_invoice_reconciliation_for_bank_txn(db, bank_txn_id))
    for payment in await payments_for_bank_txn(db, bank_txn_id):
        touched.add(payment.inv_id)
        await delete_invoice_payment(db, payment)

    # 2. Match each invoice (link = truth) and record the deposit as its payment,
    # spreading the deposit FIFO. Two amounts per invoice, kept distinct:
    #   attribution — how much of the deposit this invoice explains (its balance owing,
    #                 or its full total if already paid). Decrements `remaining` so the
    #                 deposit reads fully reconciled only when every dollar is explained.
    #   payment     — how much to actually pay down: only the outstanding balance. An
    #                 already-paid invoice is a "just match" — linked and it explains the
    #                 deposit, but NO payment is written (never double-pays it).
    invoices = []
    for i in inv_ids:
        inv = await get_invoice_by_id(db, i)
        if inv:
            invoices.append(inv)
    invoices.sort(key=_inv_sort_key)
    remaining = _to_decimal(txn.credit)
    for inv in invoices:
        touched.add(inv.id)
        await set_invoice_reconciliation(db, inv.id, bank_txn_id, True)
        balance = _to_decimal(inv.inv_balance_due if inv.inv_balance_due is not None else inv.inv_total)
        explains = balance if balance > Decimal("0") else _to_decimal(inv.inv_total)
        attribution = min(explains, remaining) if remaining > Decimal("0") else Decimal("0")
        payment = min(balance, attribution) if balance > Decimal("0") else Decimal("0")
        if payment > Decimal("0"):
            await create_inv_payment(
                zjwt,
                db,
                {
                    "inv_id": inv.id,
                    "bank_txn_id": bank_txn_id,
                    "pay_amount": float(payment),
                    "pay_date": txn.txn_date,
                    "pm_name": "Bank deposit",
                    "pay_reference": (txn.description or "")[:256],
                },
            )
        remaining -= attribution

    # 3. Recalculate paid-status (money view) for every invoice we touched.
    for inv_id in touched:
        await recalculate_invoice_payment_summary(db, inv_id)

    # 4. Deposit-level flag: reconciled ONLY when the whole deposit is explained (the
    # full credit was applied). A partially-applied deposit still has unexplained money
    # -> stays not reconciled. (No matches -> False.)
    credit = _to_decimal(txn.credit)
    fully_reconciled = credit > Decimal("0") and remaining <= Decimal("0")
    await update_bank_txn_fields(db, txn, {"is_reconciled": bool(fully_reconciled)})

    return await build_reconcile_view(zjwt, db, bank_txn_id)
