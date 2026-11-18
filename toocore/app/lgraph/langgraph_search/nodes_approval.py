# app/lgraph/langgraph_search/nodes_approval.py
import json
import logging
import re
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command, interrupt

from toocore.app.lgraph.core_tools import execute_sql, run_rag_rerank, validate_sql_select
from app.lgraph.langgraph_search.hitl_approvals import create_approval
from app.lgraph.langgraph_search.llm_decisions import SQL_MODEL, generate_sql
from app.lgraph.langgraph_search.nodes import (
    MAX_SQL_ATTEMPTS,
    _cannot_compute_response,
    _emit_status,
    _rows_are_empty,
)
from app.lgraph.langgraph_search.state import StateSearch

log = logging.getLogger(__name__)

SENSITIVE_TABLES = {"users", "payments", "employees"}   # your restricted tables
APPROVAL_TTL_DAYS = 7


# ---------- helpers ----------

def assess_risk(sql: str) -> list[str]:
    """Empty list = safe, skip approval. Crude regex; use sqlglot in production."""
    s = sql.lower()
    risks: list[str] = []
    if not s.lstrip().startswith(("select", "with")):
        risks.append("not a read-only query")
    if not re.search(r"\blimit\b", s):
        risks.append("no LIMIT clause")
    hit = sorted(t for t in SENSITIVE_TABLES if re.search(rf"\b{t}\b", s))
    if hit:
        risks.append(f"touches sensitive tables: {', '.join(hit)}")
    return risks


def _allow_rag_fallback(state: StateSearch) -> bool:
    # same rule as your old node_sql
    return not state.get("forced_sql") and "rag" not in (state.get("tried_routes") or [])


# ---------- 1. generate (LLM + guardrail, no execution) ----------

async def node_sql_generate(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    query = state.get("query") or ""
    attempts = state.get("sql_attempts", 0)
    sql_text = state.get("sql_text") or ""
    last_error = state.get("sql_error")          # set when we come back after a failed execute
    sql_rationale, sql_reasoning = None, []
    ok = False

    await _emit_status(config, "sql_start", {"query": query})

    while attempts < MAX_SQL_ATTEMPTS:
        attempts += 1
        sql_text, sql_rationale, sql_reasoning = await generate_sql(
            query,
            previous_sql=sql_text if last_error else None,
            error=last_error,
        )
        await _emit_status(config, "sql_generated", {"sql": sql_text, "attempt": attempts})

        ok, reason = validate_sql_select(sql_text)
        if ok:
            break
        last_error = f"Guardrail rejected query: {reason}"
        await _emit_status(
            config,
            "sql_guardrail_rejected",
            {"reason": reason, "sql": sql_text, "attempt": attempts},
        )

    if not ok:
        return {"sql_text": sql_text, "sql_error": last_error, "sql_attempts": attempts}

    return {
        "sql_text": sql_text,
        "sql_rationale": sql_rationale,
        "sql_reasoning": list(sql_reasoning or []),
        "sql_risks": assess_risk(sql_text),
        "sql_error": None,
        "sql_attempts": attempts,
    }


def route_after_generate(
    state: StateSearch,
) -> Literal["SQLFallback", "SQLGiveUp", "RequestApproval", "SQLExecute"]:
    if state.get("sql_error"):                    # guardrail rejected every attempt
        return "SQLFallback" if _allow_rag_fallback(state) else "SQLGiveUp"
    return "RequestApproval" if state.get("sql_risks") else "SQLExecute"


# ---------- 2. approval (request, then pause) ----------

async def node_request_approval(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    """Side effects live here: write the DB row, notify. No interrupt in this node."""
    cfg = config["configurable"]
    row = await create_approval(
        cfg["db"],
        jwt=cfg["zjwt"],
        thread_id=cfg["thread_id"],
        kind="sql_query",
        payload={
            "query": state["query"],
            "sql": state["sql_text"],
            "rationale": state.get("sql_rationale"),
            "risks": state["sql_risks"],
        },
        ttl_days=APPROVAL_TTL_DAYS,
    )
    log.info("APPROVAL NEEDED id=%s risks=%s", row.id, state["sql_risks"])   # notification stub
    await _emit_status(config, "approval_pending", {"approval_id": str(row.id)})
    return {"approval_id": str(row.id), "approval_status": "pending"}


async def node_approval_gate(
    state: StateSearch, config: RunnableConfig
) -> Command[Literal["SQLExecute", "__end__"]]:
    """The pause. Nothing but interrupt() before the decision is read."""
    decision = interrupt({
        "type": "approval_required",
        "approval_id": state["approval_id"],
        "kind": "sql_query",
    })

    action = decision.get("action")
    if action == "approve":
        return Command(update={"approval_status": "approved"}, goto="SQLExecute")

    if action == "edit":
        new_sql = decision["sql"]
        return Command(
            update={
                "sql_text": new_sql,
                "sql_risks": assess_risk(new_sql),
                "approval_status": "approved",
            },
            goto="SQLExecute",
        )

    status = "expired" if action == "expired" else "rejected"
    return Command(
        update={
            "approval_status": status,
            "response": {
                "query": state.get("query") or "",
                "route": "sql",
                "sql": state.get("sql_text"),
                "answer": f"The query was {status}; nothing was executed.",
                "confidence": 0.0,
                "citations": [],
                "evidence": [],
            },
        },
        goto=END,
    )


# ---------- 3. execute ----------

async def node_sql_execute(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    cfg = config["configurable"]
    query = state.get("query") or ""
    sql_text = state["sql_text"]

    # Last line of defence: even an approved or human-edited query goes through your guardrail
    ok, reason = validate_sql_select(sql_text)
    if not ok:
        return {"sql_error": f"Guardrail rejected query: {reason}"}

    try:
        await _emit_status(config, "sql_execute", {"sql": sql_text})
        rows = await execute_sql(cfg["db"], sql_text)
    except Exception as exc:
        await _emit_status(config, "sql_execute_failed", {"error": str(exc), "sql": sql_text})
        return {"sql_error": str(exc)}

    empty = _rows_are_empty(rows)
    combined_reasoning = list(state.get("sql_reasoning") or [])
    if state.get("sql_rationale"):
        combined_reasoning.insert(0, state["sql_rationale"])

    response = {
        "query": query,
        "route": "sql",
        "sql": sql_text,
        "top_k": state.get("top_k"),
        "model": SQL_MODEL,
        "rerank_model": "router-sql",
        "answer": json.dumps(rows, ensure_ascii=False, indent=2, default=str),
        "confidence": 1.0,
        "reasoning_summary": ["SQL executed successfully."],
        "citations": [],
        "limitations": "No matching records were found." if empty else "",
        "model_reasoning_summary": combined_reasoning,
        "evidence": [],
    }
    await _emit_status(config, "sql_done", {"row_count": len(rows or []), "model": SQL_MODEL})
    return {"sql_error": None, "sql_empty": empty, "response": response}


def route_after_execute(state: StateSearch) -> str:
    if state.get("sql_error"):
        if state.get("sql_attempts", 0) < MAX_SQL_ATTEMPTS:
            return "SQLGenerate"                  # retry with the error fed back to the LLM
        return "SQLFallback" if _allow_rag_fallback(state) else "SQLGiveUp"
    if state.get("sql_empty") and _allow_rag_fallback(state):
        return "SQLFallback"
    return END


# ---------- 4. terminal helpers (replace the old in-node fallbacks) ----------

async def node_sql_fallback(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    cfg = config["configurable"]
    sql_text = state.get("sql_text") or ""
    if state.get("sql_empty"):
        note = "SQL returned no usable result; fell back to RAG."
    else:
        note = f"SQL failed after {MAX_SQL_ATTEMPTS} attempts: {state.get('sql_error')} (fell back to RAG)"

    rag_response = await run_rag_rerank(
        state.get("query") or "",
        state.get("top_k"),
        cfg["zjwt"],
        cfg["db"],
        status_cb=cfg.get("status_cb"),
    )
    if isinstance(rag_response, dict):
        rag_response["route"] = "sql"
        rag_response["sql"] = sql_text
        rag_response["model_reasoning_summary"] = (
            [note] + list(rag_response.get("model_reasoning_summary") or [])
        )
        rag_response["limitations"] = (
            "Not computed from the database. " + str(rag_response.get("limitations") or "")
        ).strip()
    return {"response": rag_response}


async def node_sql_giveup(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    reason = f"SQL failed after {MAX_SQL_ATTEMPTS} attempts: {state.get('sql_error')}"
    return {"response": _cannot_compute_response(state, state.get("sql_text") or "", reason)}