# app/lgraph/langgraph_search/nodes_approval.py
import inspect
import logging
import re
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command, interrupt

from .hitl_approvals import create_approval
from .state import StateSearch

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


async def _emit(config: RunnableConfig, stage: str, data: dict[str, Any]) -> None:
    cb = config["configurable"].get("status_cb")
    if cb is None:                       # on a resume days later there may be no live listener
        return
    out = cb(stage, data)
    if inspect.isawaitable(out):
        await out


# ---------- nodes ----------

async def node_sql_generate(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    """Generate SQL only. Does NOT execute. Keep your fall-back-to-RAG logic here."""
    cfg = config["configurable"]
    sql_text, rationale = await _generate_sql(state["query"], cfg["db"], cfg["zjwt"])
    return {
        "sql_text": sql_text,
        "sql_rationale": rationale,
        "sql_risks": assess_risk(sql_text),
    }


def route_after_generate(state: StateSearch) -> Literal["RequestApproval", "SQLExecute"]:
    return "RequestApproval" if state.get("sql_risks") else "SQLExecute"


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
    # Notification stub: replace with email / Slack later
    log.info("APPROVAL NEEDED id=%s risks=%s", row.id, state["sql_risks"])
    await _emit(config, "approval_pending", {"approval_id": str(row.id)})
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
            "response": {"status": status, "answer": f"The query was {status}; nothing was executed."},
        },
        goto=END,
    )


async def node_sql_execute(state: StateSearch, config: RunnableConfig) -> dict[str, Any]:
    cfg = config["configurable"]
    sql = state["sql_text"]

    # Last line of defence: even an approved or edited query must be read-only
    if not sql.lstrip().lower().startswith(("select", "with")):
        return {"response": {"status": "blocked", "answer": "Only read-only queries can be executed."}}

    rows = await _run_sql(cfg["db"], sql)
    return {"response": {"status": "ok", "answer": rows}}   # adapt to your response shape


# ---------- STAND-INS: replace with your existing logic ----------

async def _generate_sql(query: str, db, jwt) -> tuple[str, str | None]:
    """Move the LLM call from your current node_sql here. Returns (sql, rationale)."""
    raise NotImplementedError


async def _run_sql(db, sql: str) -> Any:
    """Move the execution part from your current node_sql here."""
    raise NotImplementedError