from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OBankTxnOut(BaseModel):
    id: UUID
    txn_date: Optional[date] = None
    description: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    source: Optional[str] = None
    status: Optional[str] = None
    # Short formal bank abbreviation, e.g. "TD" for "TD Canada Trust".
    bank_name: Optional[str] = None
    # AI classification: opening_balance | invoice | expense | transfer | other
    type: Optional[str] = None
    note: Optional[str] = None
    # Binary reconcile flag (True only when fully applied; partial = False).
    is_reconciled: bool = False
    # Derived on read (never stored):
    applied_total: Decimal = Decimal("0")   # sum of invoice_payment.pay_amount linked here
    unapplied: Decimal = Decimal("0")       # credit - applied_total (>=0)
    paid_inv_ids: list[UUID] = []           # invoices this deposit paid
    created_at: Optional[datetime] = None


class OBankTxnCreate(BaseModel):
    id: Optional[UUID] = None
    txn_date: Optional[date] = None
    description: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    source: Optional[str] = None
    bank_name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class ReconcilePayload(BaseModel):
    """Reconcile a deposit against N invoices — a match. The client sends only the
    matched invoice ids; the backend records the deposit as their payment and runs the
    payment logic (amounts are backend-owned). Passing [] de-reconciles."""
    bank_txn_id: UUID
    inv_ids: list[UUID] = []


class ReconcileCandidate(BaseModel):
    """An outstanding invoice offered as a match for the selected deposit."""
    inv_id: UUID
    inv_number: Optional[str] = None
    inv_date: Optional[datetime] = None
    client_company_name: Optional[str] = None
    inv_total: Optional[Decimal] = None
    inv_balance_due: Optional[Decimal] = None


class ReconcileView(BaseModel):
    """Everything the reconcile panel needs for one deposit."""
    bank_txn: OBankTxnOut
    candidates: list[ReconcileCandidate] = []


class ReconcileSuggestion(BaseModel):
    """One AI-suggested invoice match for a deposit."""
    inv_id: UUID
    confidence: float = 0.0   # 0..1
    reason: Optional[str] = None


class ReconcileSuggestResult(BaseModel):
    """AI suggestions for which invoices a deposit paid (advisory, may be empty)."""
    suggestions: list[ReconcileSuggestion] = []
    model: Optional[str] = None
