i want to do an async approval hitl. you find a place to plug in this function: need huamn approval to continue. but the approval could take a week... this story will be easier to plug in any biz scenario. make sense ? do able? highlevel explain to me first

Yes, it makes sense and it’s doable. It’s also a better interview story than a synchronous approve/reject popup, because real approvals (finance, legal, security) take hours or days.

The core idea

interrupt() doesn’t keep anything running while it waits. When it fires:

The graph’s state is written to a persistent checkpointer (Postgres).
The run ends. No process, thread, or connection is held open.
A week later, someone resumes the same thread_id with Command(resume=decision), and the graph continues from that node.

So the “wait a week” part is already handled by the checkpoint. What you build is everything around the pause: how the approver finds out, how their decision gets back in, and what happens if they never respond.

The flow
User asks → agent runs → hits risky step
   → ApprovalGate node: create approval record, notify approver, interrupt()
   → run ends, user gets "Pending approval (ID 123)"

   ... hours or days pass, no compute running ...

Approver clicks link / Slack button / dashboard
   → POST /approvals/123/decision
   → server loads the thread and resumes with Command(resume=...)
   → graph continues → result delivered to the user (push or poll)
What you add beyond the interrupt
Piece	Purpose
Persistent checkpointer	State survives restarts and deploys. InMemorySaver is not enough.
Approvals table	approval_id, thread_id, kind, payload, status, requester, approver, expires_at, timestamps. This is the source of truth for “what’s pending” and doubles as the audit trail.
Notification	Email, Slack, or a dashboard item with the context needed to decide.
Resume endpoint	Authenticates the approver, checks the approval is still pending, resumes the thread. Must be idempotent so a double-click doesn’t run twice.
Timeout policy	Reminder after N days, then escalate, auto-reject, or expire. Without this, a pause can last forever.
Result delivery	The requester isn’t watching, so push a notification or let them poll by thread_id.
Where to plug it into your graph

Same place as before: just before the risky SQL runs, between generate and execute. But the better design is a generic, reusable ApprovalGate node that takes a kind and a payload (and the SQL case is just one configuration of it).

DecideRoute → SQLGenerate → [risk check] → ApprovalGate → SQLExecute
                                  └── safe? skip the gate entirely

That reusability is what makes the story easy to plug into any business scenario. The same gate works for:

Refunds above a threshold
Exporting customer data
Sending a customer-facing email or contract
Production changes
Anything that needs a manager, compliance, or security sign-off

Only the payload, the approver routing, and the timeout rules change.

The tricky parts worth knowing
Stale approvals: the SQL was approved a week ago, but the data or schema may have changed. Re-validate cheaply before executing, or carry an expiry on the approval.
Code drift: the graph may be redeployed during the wait. Keep node names stable, because the checkpoint points at a node by name.
Authorization: the resume endpoint must verify the approver is allowed to approve this kind of request. A signed link alone isn’t enough.
Duplicate resumes: guard with the approval status in the DB (pending → approved is a one-time transition).
Parallel branches: if you later use Send fan-out, several branches can wait at once, and the resume values need to match the right ones.
Is it doable in your setup?

Yes, with one caveat: your logs show langgraph dev with the in-memory runtime, which loses paused threads on restart. For a real week-long wait you’d compile with a Postgres checkpointer (or deploy to LangGraph Platform, which persists for you), and add a small FastAPI service for the approvals table and the resume endpoint. Your project already has a custom app at ./src/agent/app.py, so that’s a natural home for those endpoints.

How I’d pitch it

“Approvals in the real world take days, so I treat the pause as durable state, not an open request. The graph checkpoints to Postgres and exits. An approvals table tracks status and deadlines, a webhook resumes the thread when the approver decides, and a timeout policy handles non-response. The gate is a reusable node, so refunds, data exports, or production changes are configuration, not new code.”

If this direction works for you, I’d suggest the first version include the generic gate node, the approvals table, and the resume endpoint, with notification stubbed out (just log the link). Want me to write that?

great. you guide, i type. one file per round, after i confirm i understand continue next file. ok?

Yes. Here’s the plan, then File 1. I’m assuming we’re building on your RAG/SQL/General router graph (app/lgraph/langgraph_search/), not the research agent.

The 6 files
#	File	What it does
1	state.py	Add the new state fields
2	approvals.py	Approvals table (SQLite for now, swappable to Postgres)
3	nodes_approval.py	SQLGenerate, RequestApproval, ApprovalGate, SQLExecute
4	graph.py	Wire the nodes, add a persistent checkpointer
5	api_approvals.py	Endpoints: list pending, submit decision (resumes the graph)
6	try_it.py	Script to run, pause, “wait”, then resume

RequestApproval (creates the record, sends the notification) and ApprovalGate (only the interrupt) are separate nodes. A resumed node re-runs from its first line, and we don’t want a duplicate approval record created on every resume.

File 1: state.py

Add these fields to your existing StateSearch:

python
# app/lgraph/langgraph_search/state.py
class StateSearch(TypedDict, total=False):
    # ...keep all your existing fields (question, route, answer, answer_ok, attempts)...

    sql: str                 # the generated query waiting for approval
    sql_risks: list[str]     # why it needs approval; empty list means safe, skip the gate
    approval_id: str         # links this graph run to a row in the approvals table
    approval_status: str     # "pending" | "approved" | "rejected" | "expired"

Why each one is here:

sql_risks drives the routing. If it’s empty, the query skips approval entirely, so only risky queries ever wait.
approval_id is the bridge between the graph and the outside world. The approver acts on an approval ID, and the server uses it to look up which thread_id to resume.
approval_status lets later nodes (and the user-facing response) know what happened without querying the database.

If your StateSearch isn’t a TypedDict (for example a Pydantic model or dataclass), paste it and I’ll adapt this.

Tell me when you’ve added it and what questions you have, and I’ll send File 2 (approvals.py).

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sch_ai import JWType


class StateSearch(TypedDict, total=False):
    query: str
    top_k: int
    zjwt: JWType
    db: AsyncSession
    status_cb: Callable[[str, dict[str, Any]], Awaitable[None] | None]
    route: str
    decision: dict[str, Any]
    route_reasoning: list[str]
    rag_response: dict[str, Any]
    sql_text: str
    sql_rationale: str | None
    sql_reasoning: list[str]
    general_payload: dict[str, Any]
    general_reasoning: list[str]
    response: dict[str, Any]
    attempts: int
    answer_ok: bool
    tried_routes: list[str]


here is my current state. you refactor

I read your real state, and it changes File 1 in one important way.

The catch: db, status_cb and zjwt can’t live in state

Every superstep, the checkpointer serializes the whole state. That breaks for:

db: AsyncSession: a live connection object. It can’t be serialized, and a week later it wouldn’t exist anyway.
status_cb: a function, also not serializable.
zjwt: if it’s a token, it would be written into the checkpoint table and sit there for a week. It would also be expired by the time the approval comes back.

The fix is to move these runtime dependencies into config["configurable"]. You pass them on every ainvoke, and again on resume with fresh values. State then holds only plain data.

File 1: state.py
python
# app/lgraph/langgraph_search/state.py
from typing import Any, TypedDict


class StateSearch(TypedDict, total=False):
    # ---- inputs (plain data only: everything here is checkpointed) ----
    query: str
    top_k: int

    # ---- routing ----
    route: str
    decision: dict[str, Any]
    route_reasoning: list[str]
    tried_routes: list[str]
    attempts: int

    # ---- RAG ----
    rag_response: dict[str, Any]
    answer_ok: bool

    # ---- SQL ----
    sql_text: str
    sql_rationale: str | None
    sql_reasoning: list[str]

    # ---- general ----
    general_payload: dict[str, Any]
    general_reasoning: list[str]

    # ---- approval (new) ----
    sql_risks: list[str]      # empty = safe, skip the gate
    approval_id: str          # key into the approvals table
    approval_status: str      # "pending" | "approved" | "rejected" | "expired"

    # ---- output ----
    response: dict[str, Any]


# Runtime dependencies. NOT in state: pass via config on every invoke AND every resume.
#   config = {"configurable": {
#       "thread_id": "...",
#       "db": session,            # AsyncSession
#       "status_cb": callback,
#       "zjwt": jwt,
#   }}
# Nodes read them with:  config["configurable"]["db"]
What changed
Removed db, status_cb and zjwt from state. They move to config.
Added sql_risks, approval_id and approval_status. I reused your names, so the SQL text is sql_text and the output is response, not what I wrote earlier.
Everything else is untouched.
What this means for your existing code

Your existing nodes (node_rag, node_sql, node_orchestration and so on) currently read state["db"] and similar. Each one needs a one-line change to read from config instead. I’ll handle that in the graph wiring round so you do it once. Until then, don’t run the graph with a checkpointer.

One question before File 2: what’s inside JWType, and which field identifies the user who asked? The approvals table needs a requester_id, and I want to take it from the right place.

from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JWType(BaseModel):
    zuid: UUID | None = None
    ztid: UUID | None = None
    zbid: UUID | None = None
    zcid: UUID | None = None
    zemail: str | None = None

    app_metadata: dict[str, Any] = Field(default_factory=dict)
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class RagHit(BaseModel):
    evidence_id: int
    score: Optional[float] = None 
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    hybrid_score: Optional[float] = None
    source_id: str
    chunk: str
    history: dict[str, Any]


class RagRetrieveRes(BaseModel):
    query: str
    top_k: int
    mode: Literal["vector", "keyword", "hybrid"]
    results: List[RagHit]


userid, tenentid, bizid, customerid, email from jwt

Mapping confirmed, and it settles who owns what:

JWT field	Used as
zuid	requester_id, and later decided_by for the approver
ztid	tenant_id. Every query filters on it, so a tenant-A approver can never see or act on tenant-B approvals
zbid, zcid	stored for context and filtering
zemail	requester_email, used to notify the requester of the outcome

We store these ids, not the JWT itself. A week-old token would be expired anyway, and it shouldn’t sit in a table.

File 2: approvals.py

This is the source of truth for “what’s pending”, and it doubles as the audit trail.

python
# app/lgraph/langgraph_search/approvals.py
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, Uuid, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas.sch_ai import JWType


class Base(DeclarativeBase):          # replace with your project's existing Base
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # who / where (all from the JWT at request time)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    biz_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    requester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    requester_email: Mapped[str | None] = mapped_column(String)

    # which paused graph run this belongs to
    thread_id: Mapped[str] = mapped_column(String, index=True)

    # what needs approving (generic: "sql_query", "refund", "data_export", ...)
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    # lifecycle
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSON)


async def create_approval(
    db: AsyncSession,
    *,
    jwt: JWType,
    thread_id: str,
    kind: str,
    payload: dict[str, Any],
    ttl_days: int = 7,
) -> Approval:
    row = Approval(
        tenant_id=jwt.ztid,
        biz_id=jwt.zbid,
        customer_id=jwt.zcid,
        requester_id=jwt.zuid,
        requester_email=jwt.zemail,
        thread_id=thread_id,
        kind=kind,
        payload=payload,
        expires_at=_now() + timedelta(days=ttl_days),
    )
    db.add(row)
    await db.commit()          # must be durable BEFORE the graph pauses
    await db.refresh(row)
    return row


async def get_approval(
    db: AsyncSession, approval_id: uuid.UUID, tenant_id: uuid.UUID | None
) -> Approval | None:
    q = select(Approval).where(
        Approval.id == approval_id, Approval.tenant_id == tenant_id
    )
    return (await db.execute(q)).scalar_one_or_none()


async def list_pending(db: AsyncSession, tenant_id: uuid.UUID | None) -> list[Approval]:
    q = (
        select(Approval)
        .where(Approval.tenant_id == tenant_id, Approval.status == "pending")
        .order_by(Approval.created_at)
    )
    return list((await db.execute(q)).scalars())


async def decide(
    db: AsyncSession,
    *,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID | None,
    approver_id: uuid.UUID | None,
    new_status: str,                       # "approved" | "rejected"
    decision: dict[str, Any],
) -> bool:
    """One-time transition pending -> approved/rejected.

    Returns False if it was already decided or expired, so a double-click or a
    late click can never trigger a second resume.
    """
    result = await db.execute(
        update(Approval)
        .where(
            Approval.id == approval_id,
            Approval.tenant_id == tenant_id,
            Approval.status == "pending",
            Approval.expires_at > _now(),
        )
        .values(
            status=new_status,
            decided_by=approver_id,
            decided_at=_now(),
            decision=decision,
        )
    )
    await db.commit()
    return result.rowcount == 1


async def expire_overdue(db: AsyncSession) -> list[Approval]:
    """Flip overdue pending rows to 'expired' and return them (for a scheduled job)."""
    q = select(Approval).where(
        Approval.status == "pending", Approval.expires_at <= _now()
    )
    rows = list((await db.execute(q)).scalars())
    for r in rows:
        r.status = "expired"
        r.decided_at = _now()
    await db.commit()
    return rows
What to notice
decide() is the idempotency guard. The UPDATE ... WHERE status = 'pending' is atomic, so if two clicks race, exactly one gets rowcount == 1. Only the winner resumes the graph (File 5).
expires_at is checked in the same UPDATE. A week-old click on an expired approval fails cleanly instead of resuming stale work.
kind and payload are generic. SQL is just kind="sql_query" with {"sql": ..., "risks": [...]}, and a refund would be another kind. That’s what makes the gate reusable.
create_approval commits before returning. The row has to exist before the graph pauses, otherwise a crash could leave a paused run nobody can approve.
Tenant filtering is the first security layer. File 5 adds the second: checking that this user is allowed to approve this kind.

Two practical notes:

Swap in your existing Base and add the table through your migration tool (Alembic or similar). Base.metadata.create_all works for a quick local test.
Uuid and JSON are SQLAlchemy 2.0 generic types and work on both Postgres and SQLite.

Tell me when you’ve got it in and what’s unclear, then I’ll send File 3 (nodes_approval.py).

only changed name: 

# app/lgraph/langgraph_search/hitl_approvals.py

all others kept. next

File 3: nodes_approval.py

I haven’t seen your current node_sql, so two functions at the bottom are stand-ins for your existing SQL logic. Everything else is final.

python
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
What to notice
The old node_sql becomes three nodes. Generation and execution are split so a resume never re-runs the LLM. The approval step gets its own two nodes: RequestApproval and ApprovalGate.
RequestApproval and ApprovalGate are separate on purpose. When the graph resumes, it restarts the node that was paused, which is ApprovalGate. If the DB write lived in the same node, every resume would create a duplicate approval row.
The interrupt payload is tiny. It carries only approval_id and kind. The full SQL and risks live in the approvals table, which is what the approver’s UI reads.
Safe queries skip the whole thing. route_after_generate sends them straight to SQLExecute, so only risky ones ever wait.
approve vs edit vs reject vs expired are the four resume values. File 5 produces them. expired will come from the timeout job.
node_sql_execute has a hard guard. It blocks non-read-only SQL even after approval, so a human edit can’t smuggle in a DELETE.
Runtime dependencies come from config. db, zjwt and status_cb are read from config["configurable"], and thread_id is read from the same place.
Two things I need from you
Paste your current node_sql so I can map the two stand-ins exactly, including how you build the response dict and where the RAG fallback sits.
Confirm the nodes are async in your codebase (your db is an AsyncSession, so I assume yes).

Once that’s settled, I’ll send File 4 (graph.py), which wires these nodes and adds the persistent checkpointer.

