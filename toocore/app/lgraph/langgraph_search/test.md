Step 2: change your existing endpoint (the first-run side)

Wherever you call compiled_workflow.ainvoke(...) today:

python
thread_id = str(uuid.uuid4())
config = {"configurable": {
    "thread_id": thread_id, "db": db, "zjwt": jwt, "status_cb": status_cb,
}}
result = await request.app.state.graph.ainvoke({"query": query, "top_k": top_k}, config)

if result.get("__interrupt__"):
    return {
        "status": "pending_approval",
        "approval_id": result["__interrupt__"][0].value["approval_id"],
        "thread_id": thread_id,
    }
return result["response"]

db, zjwt and status_cb leave the input dict, and the response is “pending approval” when the graph paused. The UI needs a small branch for that status.

Step 3: create expiry_job.py

python
# app/lgraph/langgraph_search/expiry_job.py
import asyncio
import logging

from langgraph.types import Command

from app.lgraph.langgraph_search.hitl_approvals import expire_overdue
from app.schemas.sch_ai import JWType

log = logging.getLogger(__name__)


async def expire_and_resume(graph, session_factory) -> int:
    async with session_factory() as db:
        rows = await expire_overdue(db)          # flips pending -> expired, commits
        for row in rows:
            requester = JWType(
                zuid=row.requester_id, ztid=row.tenant_id, zbid=row.biz_id,
                zcid=row.customer_id, zemail=row.requester_email,
            )
            config = {"configurable": {"thread_id": row.thread_id, "db": db, "zjwt": requester}}
            try:
                await graph.ainvoke(Command(resume={"action": "expired"}), config)
            except Exception:
                log.exception("expiry resume failed approval_id=%s", row.id)
        return len(rows)


async def expiry_loop(graph, session_factory, every_seconds: int = 300) -> None:
    while True:
        try:
            n = await expire_and_resume(graph, session_factory)
            if n:
                log.info("expired %d approvals", n)
        except Exception:
            log.exception("expiry loop error")
        await asyncio.sleep(every_seconds)

Start it in your lifespan from File 5, right after app.state.graph = graph:

python
task = asyncio.create_task(expiry_loop(graph, session_factory))   # your async_sessionmaker
yield
task.cancel()

Known gaps (production items, not blockers)

Several app instances: each would run the expiry loop, and expire_overdue is select-then-update, so two could resume the same thread. Run the loop in one place, or add FOR UPDATE SKIP LOCKED to that select.
Resume failure: if a resume crashes after the DB row is decided, the row and the graph disagree. A repair job could find decided rows whose thread still has next == ("ApprovalGate",) and re-resume them.
Notification: RequestApproval only logs the approval link. Wire Slack or email there.
Dead code: after the tests pass, delete the old node_sql and _rag_fallback from nodes.py.

That completes the six files. Run the three tests above and paste any traceback, and I’ll help fix it.