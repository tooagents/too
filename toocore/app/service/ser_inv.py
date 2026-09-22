from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_nvoice import InvoiceDB
from app.db.models.inv.i_nvoice_item import InvoiceItemDB
from app.db.models.inv.i_nvoice_payment import InvoicePaymentDB
from app.db.models.too.z_be import ZBizEntityDB
from app.db.repo.repo_inv_item import create_invoice_item, list_invoice_items
from app.db.repo.repo_inv import (create_invoice,get_invoice_by_id,list_invoices,
                                  list_recent_invoices_by_client,update_invoice_fields,)
from app.db.repo.repo_inv_payment import (create_invoice_payment,list_invoice_payments,)
from app.db.repo.repo_inv_payment import (delete_invoice_payment,get_invoice_payment_by_id,)
from app.schemas.sch_ai import JWType
from app.service.ser_inv_clone_ai import suggest_next_period

_INVOICE_COLUMNS = set(InvoiceDB.__table__.columns.keys())
_INVOICE_ITEM_COLUMNS = set(InvoiceItemDB.__table__.columns.keys())
_INVOICE_PAYMENT_COLUMNS = set(InvoicePaymentDB.__table__.columns.keys())


@dataclass(slots=True)
class InvoiceAggregate:
    invoice: InvoiceDB
    items: list[InvoiceItemDB]
    payments: list[InvoicePaymentDB]


async def fetch_invoices(db: AsyncConnection) -> list[InvoiceDB]:
    return await list_invoices(db)


def _to_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return bool(value)


def _base_ids(zjwt: JWType) -> dict[str, UUID|None]:
    return {
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zuid,
        "usr_id": zjwt.zuid,
        "cli_id": zjwt.zuid,
        "created_by": zjwt.zuid,
    }


async def _next_invoice_number(zjwt: JWType, db: AsyncConnection) -> str | None:
    table = ZBizEntityDB.__table__
    result = await db.execute(
        select(table.c.be_inv_prefix, table.c.be_inv_integer, table.c.be_inv_integer_max)
        .where(table.c.id == zjwt.zuid)
        .with_for_update()
    )
    row = result.mappings().one_or_none()
    if not row:
        return None

    prefix = row["be_inv_prefix"] or "INV-"
    current = row["be_inv_integer"] or row["be_inv_integer_max"] or 1
    next_value = current + 1
    await db.execute(
        update(table)
        .where(table.c.id == zjwt.zuid)
        .values(
            be_inv_integer=next_value,
            be_inv_integer_max=max(next_value, row["be_inv_integer_max"] or next_value),
        )
    )
    return f"{prefix}{current}"


async def fetch_invoice_by_id(zjwt: JWType, db: AsyncConnection, inv_id: UUID) -> InvoiceAggregate | None:
    inv = await get_invoice_by_id(db, inv_id)
    if not inv:return None
    items, payments = await asyncio.gather(
        list_invoice_items(db, inv_id),
        list_invoice_payments(db, inv_id),
    )
    return InvoiceAggregate(invoice=inv, items=items, payments=payments)


async def create_or_update_invoice(zjwt: JWType, db: AsyncConnection, payload: dict) -> InvoiceDB:
    data = dict(payload)
    inv_id = _to_uuid(data.pop("inv_id", None) or data.get("id"))
    if inv_id:
        data["id"] = inv_id

    if "be_id" in data and "biz_id" not in data:
        data["biz_id"] = data.pop("be_id")
    if "user_id" in data and "usr_id" not in data:
        data["usr_id"] = data.pop("user_id")
    if "is_locked" in data:
        data["is_flag"] = _to_bool(data.pop("is_locked"))
    if "is_deleted" in data:
        data["is_deleted"] = _to_bool(data.get("is_deleted"))
    if "client_id" in data:
        data["client_id"] = _to_uuid(data.get("client_id"))

    data.pop("is_active", None)
    data.pop("inv_items", None)
    data.pop("inv_payments", None)
    data.pop("created_at", None)
    data.pop("updated_at", None)

    filtered = {k: v for k, v in data.items() if k in _INVOICE_COLUMNS}
    inv_id = _to_uuid(filtered.get("id"))
    if inv_id:
        existing = await get_invoice_by_id(db, inv_id)
        if existing:
            updates = {
                k: v
                for k, v in filtered.items()
                if k
                not in {
                    "id",
                    "ten_id",
                    "biz_id",
                    "usr_id",
                    "cli_id",
                    "created_by",
                    "created_at",
                }
            }
            return await update_invoice_fields(db, existing, updates)

    create_payload = {**filtered, **_base_ids(zjwt)}
    if not create_payload.get("inv_number"):
        create_payload["inv_number"] = await _next_invoice_number(zjwt, db)
    return await create_invoice(db, create_payload)


async def soft_delete_invoice(zjwt: JWType, db: AsyncConnection, inv_id: UUID) -> InvoiceDB:
    inv = await get_invoice_by_id(db, inv_id)
    if not inv:
        raise ValueError("Invoice not found")
    return await update_invoice_fields(db, inv, {"is_deleted": True})


def _copy_model_payload(model: Any, source: Any, skip: set[str]) -> dict[str, Any]:
    return {
        column.key: getattr(source, column.key)
        for column in model.__table__.columns
        if column.key not in skip
    }


def _iso_date(value: Any) -> str | None:
    """A DateTime column value -> 'YYYY-MM-DD' for the AI prompt."""
    if value is None:
        return None
    try:
        return value.isoformat()[:10]
    except (AttributeError, ValueError):
        return None


def _as_datetime(value: date | None) -> datetime | None:
    """A date from the AI suggestion -> tz-aware datetime for a timestamptz column."""
    if value is None:
        return None
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _item_texts(items: list[InvoiceItemDB]) -> list[str]:
    """Free-text on line items where a service period might be written."""
    texts: list[str] = []
    for item in items:
        for value in (item.item_name, item.item_description, item.item_note):
            text = str(value).strip() if value else ""
            if text:
                texts.append(text)
    return texts


async def _suggest_next_period_for(
    db: AsyncConnection, invoice: InvoiceDB
) -> dict[str, Any] | None:
    """Best-effort next-issue-date suggestion from the client's recent invoices.

    Looks back over the client's last 3 invoices (fewer if that's all there is)
    so the clone tracks the client's *current* cadence. A service period may be
    stated anywhere free-text — the reference, the notes, or a line item — so we
    feed the detector each invoice's item text and notes too, not just the
    reference/date columns. Returns None whenever a suggestion can't be made, so
    the caller copies the source dates verbatim.
    """
    # client_id is often null on invoices; fall back to the denormalized client
    # identity (email, then company name) so the pattern lookup still works.
    recent = await list_recent_invoices_by_client(
        db,
        client_id=invoice.client_id,
        client_email=invoice.client_email,
        client_company_name=invoice.client_company_name,
        limit=3,
    )
    if not recent:
        recent = [invoice]
    # Line items live in a separate table; pull them for every recent invoice so
    # a period written in an item description is visible to the detector.
    item_lists = await asyncio.gather(
        *(list_invoice_items(db, inv.id) for inv in recent)
    )
    payload = [
        {
            "inv_reference": inv.inv_reference,
            "inv_notes": inv.inv_notes,
            "item_texts": _item_texts(items),
            "inv_date": _iso_date(inv.inv_date),
            "inv_due_date": _iso_date(inv.inv_due_date),
            "inv_payment_term": inv.inv_payment_term,
        }
        for inv, items in zip(recent, item_lists)
    ]
    return await suggest_next_period(payload)


async def duplicate_invoice(zjwt: JWType, db: AsyncConnection, inv_id: UUID) -> InvoiceAggregate:
    source = await fetch_invoice_by_id(zjwt, db, inv_id)
    if not source:
        raise ValueError("Invoice not found")
    if _to_bool(source.invoice.is_deleted):
        raise ValueError("Cannot duplicate a deleted invoice")

    invoice_payload = _copy_model_payload(
        InvoiceDB,
        source.invoice,
        {
            "id",
            "created_at",
            "inv_number",
            "inv_paid_total",
            "inv_balance_due",
            "inv_payment_status",
        },
    )
    # Infer the next issue date from the client's recent invoices: the period's
    # ending date when a service period is stated anywhere on the invoice, else a
    # best-effort guess. Best-effort — a None here keeps the copied dates, and the
    # reference is only replaced when the period actually lived in it.
    next_period = await _suggest_next_period_for(db, source.invoice)

    invoice_payload.update(
        {
            **_base_ids(zjwt),
            "inv_number": await _next_invoice_number(zjwt, db),
            # Payment info belongs to the original issue, never the fresh clone.
            "inv_deposit": 0,
            "inv_paid_total": 0,
            "inv_balance_due": source.invoice.inv_total,
            "inv_payment_status": "unpaid",
            "is_deleted": False,
            "is_flag": False,
        }
    )
    if next_period:
        invoice_payload["inv_date"] = _as_datetime(next_period["inv_date"])
        if next_period.get("inv_due_date") is not None:
            invoice_payload["inv_due_date"] = _as_datetime(next_period["inv_due_date"])
        if next_period.get("inv_reference"):
            invoice_payload["inv_reference"] = next_period["inv_reference"]

    new_invoice = await create_invoice(
        db,
        {k: v for k, v in invoice_payload.items() if k in _INVOICE_COLUMNS},
    )

    new_items: list[InvoiceItemDB] = []
    for item in source.items:
        if _to_bool(item.is_deleted):
            continue
        item_payload = _copy_model_payload(
            InvoiceItemDB, item, {"id", "created_at", "inv_id"}
        )
        item_payload.update(
            {**_base_ids(zjwt), "inv_id": new_invoice.id, "is_deleted": False, "is_flag": False}
        )
        new_items.append(
            await create_invoice_item(
                db,
                {k: v for k, v in item_payload.items() if k in _INVOICE_ITEM_COLUMNS},
            )
        )

    return InvoiceAggregate(invoice=new_invoice, items=new_items, payments=[])


async def fetch_invoice_payments(db: AsyncConnection, inv_id: UUID) -> list[InvoicePaymentDB]:
    return await list_invoice_payments(db, inv_id)


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _compute_payment_status(total: Decimal, paid: Decimal) -> str:
    if paid <= Decimal("0"):
        return "unpaid"
    if paid < total:
        return "partial"
    return "Paid"


async def recalculate_invoice_payment_summary(db: AsyncConnection, inv_id: UUID) -> None:
    inv = await get_invoice_by_id(db, inv_id)
    if not inv:
        raise ValueError("Invoice not found for payment update")

    payments = await list_invoice_payments(db, inv_id)
    paid_total = Decimal("0")
    for payment in payments:
        if _to_bool(getattr(payment, "is_deleted", False)):
            continue
        paid_total += _to_decimal(payment.pay_amount)

    inv_total = _to_decimal(inv.inv_total)
    balance_due = inv_total - paid_total
    if balance_due < Decimal("0"):
        balance_due = Decimal("0")

    updates = {
        "inv_paid_total": float(paid_total),
        "inv_balance_due": float(balance_due),
        "inv_payment_status": _compute_payment_status(inv_total, paid_total),
    }
    await update_invoice_fields(db, inv, updates)


async def create_inv_payment(zjwt: JWType, db: AsyncConnection, payload: dict) -> InvoicePaymentDB:
    data = dict(payload)

    inv_id = _to_uuid(data.get("inv_id"))
    if not inv_id: raise ValueError("inv_id is required and must be a valid UUID")
    data["inv_id"] = inv_id

    # Payment creation is owned by JWT context, not request payload.
    data.pop("id", None)
    data.pop("payment_id", None)
    data.pop("ten_id", None)
    data.pop("biz_id", None)
    data.pop("usr_id", None)
    data.pop("created_by", None)

    data["pm_id"] = _to_uuid(data.get("pm_id"))
    if "is_locked" in data:data["is_flag"] = _to_bool(data.pop("is_locked"))
    if "is_deleted" in data:data["is_deleted"] = _to_bool(data.get("is_deleted"))

    data.pop("is_active", None)
    data.pop("updated_at", None)

    filtered = {k: v for k, v in data.items() if k in _INVOICE_PAYMENT_COLUMNS}
    create_payload = {
        **filtered,
        "ten_id": zjwt.ztid,
        "biz_id": zjwt.zuid,
        "usr_id": zjwt.zuid,
        "cli_id": zjwt.zuid,
        "created_by": zjwt.zuid,
    }
    return await create_invoice_payment(db, create_payload)


async def delete_inv_payment(zjwt: JWType, db: AsyncConnection, payment_id: UUID) -> UUID:
    payment = await get_invoice_payment_by_id(db, payment_id, zjwt)
    if not payment:
        raise ValueError("Invoice payment not found")
    inv_id = payment.inv_id
    await delete_invoice_payment(db, payment)
    await recalculate_invoice_payment_summary(db, inv_id)
    return inv_id
