# try_it.py      run:  python try_it.py [approve|reject]
import asyncio
import sys
import uuid

from langgraph.types import Command
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.lgraph.langgraph_search.graph import open_graph
from app.lgraph.langgraph_search.hitl_approvals import Base, decide
from app.schemas.sch_ai import JWType

PG_URL = "postgresql://user:pass@host:5432/db"            # for the checkpointer (psycopg)
SA_URL = "postgresql+asyncpg://user:pass@host:5432/db"    # for your SQLAlchemy session

TENANT = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
REQUESTER = uuid.UUID("00000000-0000-0000-0000-000000000001")
APPROVER = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Pick something your router sends to SQL and that trips assess_risk
# (touches payments/users, or has no LIMIT).
QUESTION = "List all payments with the customer email"

ACTION = sys.argv[1] if len(sys.argv) > 1 else "approve"


def print_status(stage, data):
    print(f"   [status] {stage} {data}")


async def main() -> None:
    engine = create_async_engine(SA_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:                    # quick local setup only
        await conn.run_sync(Base.metadata.create_all)

    requester = JWType(zuid=REQUESTER, ztid=TENANT, zemail="requester@example.com")
    thread_id = str(uuid.uuid4())

    # ---------------- PHASE 1: run until the graph pauses ----------------
    print("PHASE 1: asking the question")
    async with open_graph(PG_URL) as graph, Session() as db:
        config = {"configurable": {
            "thread_id": thread_id, "db": db, "zjwt": requester, "status_cb": print_status,
        }}
        result = await graph.ainvoke({"query": QUESTION, "top_k": 5}, config)

        interrupts = result.get("__interrupt__")
        if not interrupts:
            print("No approval needed (safe query or other route). Response:")
            print(result.get("response"))
            return

        approval_id = uuid.UUID(interrupts[0].value["approval_id"])
        snap = await graph.aget_state(config)
        print(f"-> PAUSED. approval_id={approval_id}  next node={snap.next}")

    # The graph, checkpointer connection and DB session are all closed here.
    # Nothing is running. In real life this gap is hours or days.
    print("\n...pretend a week passes (everything above is closed)...\n")

    # ---------------- PHASE 2: approver decides, graph resumes ----------------
    print(f"PHASE 2: approver chooses '{ACTION}'")
    async with open_graph(PG_URL) as graph, Session() as db:
        new_status = "rejected" if ACTION == "reject" else "approved"
        won = await decide(
            db, approval_id=approval_id, tenant_id=TENANT, approver_id=APPROVER,
            new_status=new_status, decision={"action": ACTION},
        )
        print(f"-> decide() won the one-time transition: {won}")

        # fresh dependencies: no status_cb, a new session, same thread_id
        config = {"configurable": {"thread_id": thread_id, "db": db, "zjwt": requester}}
        result = await graph.ainvoke(Command(resume={"action": ACTION}), config)
        resp = result.get("response") or {}
        print("-> RESULT:", resp.get("answer"))

        # a second click must lose
        again = await decide(
            db, approval_id=approval_id, tenant_id=TENANT, approver_id=APPROVER,
            new_status="approved", decision={"action": "approve"},
        )
        print(f"-> double-click won? {again}   (should be False)")

    await engine.dispose()


asyncio.run(main())