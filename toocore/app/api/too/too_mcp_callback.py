from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings_singleton
from app.core.auth import get_zjwt
from app.db.conn.db_async import get_db_admin
from app.schemas.sch_ai import JWType
from app.service.acc.transaction2je import create_transaction_and_journal_from_message

from ...db.models.acc.ac_mcp import get_recent_bank_transactions

mcpRou = APIRouter(prefix="/mcpcallback", tags=["mcp"])
settings = get_settings_singleton()


class OCRRequest(BaseModel):
    text: str


class Transaction2JERequest(BaseModel):
    message: str


def _require_internal_service(request: Request) -> None:
    expected = settings.INTERNAL_SERVICE_KEY
    if not expected:
        return
    provided = request.headers.get("X-Internal-Service-Key")
    if not provided or provided != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal service key")


@mcpRou.get("/health")
async def health(request: Request) -> dict[str, object]:
    # Local MCP-tool surface health. Agent connectivity is checked by /too/agent/diagnostics.
    local_url = str(request.url)
    caller_url = request.headers.get("origin") or request.headers.get("referer")
    service_name = request.url.hostname or "t4too_fastapi"

    health_check = {
        "url": local_url,
        "base_url": str(request.base_url),
        "service": service_name,
        "status": "ok",
    }
    if caller_url:
        health_check["caller_url"] = caller_url

    return {
        "status": "ok",
        "checks": {
            "mcp_tools": health_check,
        },
    }


@mcpRou.get("/vendors/lookup")
async def lookup_vendor(
    name: str,
    db: AsyncSession = Depends(get_db_admin),
) -> dict[str, str]:
    # row = await get_vendor_by_name(db, name)
    # if row is None:
    #     raise HTTPException(status_code=404, detail=f"Vendor '{name}' not found")

    return {
        "name": "row.name",
        "category": "row.category",
        "risk_level": "row.risk_level",
        "status": "row.status",
    }


@mcpRou.get("/bank/query")
async def query_bank(
    account_name: str,
    db: AsyncSession = Depends(get_db_admin),
) -> dict[str, object]:
    rows = await get_recent_bank_transactions(db, account_name=account_name, limit=5)
    items = [
        {
            "account_name": row.account_name,
            "description": row.description,
            "amount": float(row.amount),
            "currency": row.currency,
            "posted_at": row.posted_at.isoformat(),
        }
        for row in rows
    ]
    balance_hint = sum(item["amount"] for item in items)
    return {
        "account_name": account_name,
        "recent_transactions": items,
        "recent_net_change": balance_hint,
    }


@mcpRou.post("/ocr/extract")
def ocr_extract(payload: OCRRequest) -> dict[str, object]:
    words = payload.text.strip().split()
    return {
        "raw_text": payload.text,
        "word_count": len(words),
        "uppercase_preview": payload.text.upper()[:80],
    }


# {
#   "message": "Uber $25 today"
# }

@mcpRou.post("/transaction2je")
async def transaction2je(
    payload: Transaction2JERequest,
    request: Request,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncSession = Depends(get_db_admin),
) -> dict[str, object]:
    _require_internal_service(request)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")
    if not zjwt.ztid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tenant id in JWT")

    return await create_transaction_and_journal_from_message(db=db, zjwt=zjwt, message=message)
