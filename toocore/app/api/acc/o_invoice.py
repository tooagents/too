from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_acc_obank import ReconcileCandidate
from app.schemas.sch_ai import JWType
from app.service.ser_inv import fetch_invoices

# Statuses that still owe money.
_OUTSTANDING_STATUSES = {"unpaid", "partial", None}


router = APIRouter(prefix="/o_invoice", tags=["o_invoice"])


@router.get("/get_list", response_model=list[ReconcileCandidate])
async def get_invoice_list(
    outstanding_only: bool = False,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    """Invoices for the bank-reconcile UI. Reuses the existing invoice store;
    optionally narrows to invoices that still owe money."""
    invoices = await fetch_invoices(db)
    out = []
    for inv in invoices:
        status = (inv.inv_payment_status or "").lower() or None
        if outstanding_only and status not in _OUTSTANDING_STATUSES:
            continue
        out.append(
            ReconcileCandidate(
                inv_id=inv.id,
                inv_number=inv.inv_number,
                inv_date=inv.inv_date,
                client_company_name=inv.client_company_name,
                inv_total=inv.inv_total,
                inv_balance_due=inv.inv_balance_due,
            )
        )
    return out
