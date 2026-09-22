import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_acc_obank import (
    OBankTxnCreate,
    OBankTxnOut,
    ReconcilePayload,
    ReconcileSuggestResult,
    ReconcileView,
)
from app.schemas.sch_ai import JWType
from app.service.acc.o_bank_ai import next_ai_model, interpret_bank_text
from app.service.acc.o_bank_txn import (
    build_reconcile_view,
    create_or_update_bank_txn,
    delete_bank_txn,
    fetch_bank_txns,
    reconcile_deposit,
    suggest_reconcile_matches,
)

logger = logging.getLogger("app.http")

router = APIRouter(prefix="/o_bankstatement", tags=["o_bankstatement"])


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _format_sse_comment(comment: str) -> str:
    return f": {comment}\n\n"


class InterpretIn(BaseModel):
    text: str = Field(min_length=1)


def _row_meta(row: dict[str, Any]) -> dict[str, Any]:
    """Compact, JSON-safe view of one interpreted row for SSE meta."""
    return {
        "type": row.get("type") or "other",
        "txn_date": row["txn_date"].isoformat() if row.get("txn_date") else None,
        "description": row.get("description") or "",
        "bank_name": row.get("bank_name"),
        "debit": str(row["debit"]) if row.get("debit") is not None else None,
        "credit": str(row["credit"]) if row.get("credit") is not None else None,
        "balance": str(row["balance"]) if row.get("balance") is not None else None,
    }


def _parse_uuid_or_400(value: str, field: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field} must be a valid UUID") from exc


@router.get("/get_list", response_model=list[OBankTxnOut])
async def get_bank_txn_list(
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    return await fetch_bank_txns(zjwt, db)


@router.post("/post_one", response_model=OBankTxnOut)
async def post_bank_txn(
    payload: OBankTxnCreate,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    return await create_or_update_bank_txn(zjwt, db, payload.model_dump(exclude_unset=True))


@router.delete("/{bank_txn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_txn_route(
    bank_txn_id: str,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
) -> None:
    txn_uuid = _parse_uuid_or_400(bank_txn_id, "bank_txn_id")
    try:
        await delete_bank_txn(zjwt, db, txn_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/interpret_stream")
async def interpret_stream(
    payload: InterpretIn,
    request: Request,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
) -> StreamingResponse:
    """Interpret pasted/typed bank text with Gemini and import each row.

    Streams Server-Sent Events so the composer can narrate the AI's reading in
    real time (mirrors /acc/add2inbox_stream). Each interpreted row is saved via
    the same create path as manual entry, then reported back.
    """
    text = payload.text.strip()
    # Hard-rotate: draw this call's model up front (advances the global cursor once)
    # so we can announce the exact model being used, not a static label.
    chosen = next_ai_model()
    model = chosen[1]

    async def event_stream():
        yield _format_sse("status", {"status": "start", "meta": {"model": model}})
        await asyncio.sleep(0.02)
        try:
            if not text:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")

            yield _format_sse("status", {"status": "reading_text", "meta": {"characters": len(text)}})
            await asyncio.sleep(0.02)
            yield _format_sse("status", {"status": "calling_ai_model", "meta": {"model": model}})

            logger.info("o_bankstatement interpret_stream calling AI model=%s", model)
            rows, model_used = await interpret_bank_text(text, chosen)
            logger.info("o_bankstatement interpret_stream interpreted rows=%s model=%s", len(rows), model_used)

            if await request.is_disconnected():
                return

            yield _format_sse("status", {"status": "transactions_found", "meta": {"count": len(rows)}})
            await asyncio.sleep(0.02)

            saved: list[dict[str, Any]] = []
            for row in rows:
                if await request.is_disconnected():
                    return
                created = await create_or_update_bank_txn(
                    zjwt,
                    db,
                    {
                        "txn_date": row["txn_date"],
                        "description": row["description"],
                        "debit": row["debit"],
                        "credit": row["credit"],
                        "balance": row["balance"],
                        "bank_name": row.get("bank_name"),
                        "type": row["type"],
                        "source": "ai_paste",
                    },
                )
                saved.append(created)
                yield _format_sse("status", {"status": "row_saved", "meta": _row_meta(row)})
                await asyncio.sleep(0.02)

            first_id = str(saved[0]["id"]) if saved else None
            yield _format_sse("status", {"status": "import_summary", "meta": {"imported_count": len(saved)}})
            await asyncio.sleep(0.02)
            yield _format_sse("final", {
                "response": {
                    "model": model_used,
                    "imported_count": len(saved),
                    "first_id": first_id,
                    "transactions": [_row_meta(r) for r in rows],
                }
            })
        except HTTPException as exc:
            yield _format_sse("error", {"message": str(exc.detail)})
        except Exception as exc:  # noqa: BLE001
            logger.exception("o_bankstatement interpret_stream failed", exc_info=exc)
            yield _format_sse("error", {"message": "internal_error"})
        finally:
            if not await request.is_disconnected():
                yield _format_sse_comment(f"done {datetime.now(timezone.utc).isoformat()}")

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@router.get("/get_reconcile_view", response_model=ReconcileView)
async def get_reconcile_view(
    bank_txn_id: str,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    txn_uuid = _parse_uuid_or_400(bank_txn_id, "bank_txn_id")
    try:
        return await build_reconcile_view(zjwt, db, txn_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/suggest_reconcile", response_model=ReconcileSuggestResult)
async def get_suggest_reconcile(
    bank_txn_id: str,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    """AI suggestion of which invoices a deposit paid. Advisory — returns an empty
    list (not an error) when the AI is unavailable or finds no credible match."""
    txn_uuid = _parse_uuid_or_400(bank_txn_id, "bank_txn_id")
    try:
        return await suggest_reconcile_matches(zjwt, db, txn_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reconcile", response_model=ReconcileView)
async def post_reconcile(
    payload: ReconcilePayload,
    zjwt: JWType = Depends(get_zjwt),
    db: AsyncConnection = Depends(get_rls_conn),
):
    try:
        return await reconcile_deposit(zjwt, db, payload.bank_txn_id, payload.inv_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
