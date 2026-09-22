from fastapi import APIRouter

from . import (
    o_bankstatement,
    o_invoice,
    r_bankstatement,
    r_coa,
    r_health,
    r_journal_entries,
    r_periods,
    r_reports,
    r_transaction,
)

rouAcc = APIRouter()
rouAcc.include_router(r_health.router)
rouAcc.include_router(r_coa.router)
rouAcc.include_router(r_transaction.rouTransaction)
rouAcc.include_router(r_journal_entries.router)
rouAcc.include_router(r_reports.router)
rouAcc.include_router(r_periods.router)
rouAcc.include_router(r_bankstatement.router)
rouAcc.include_router(o_bankstatement.router)
rouAcc.include_router(o_invoice.router)
