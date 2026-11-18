from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.lgraph.langgraph_search.graph import open_graph
from app.lgraph.langgraph_search.api_approvals import router as approvals_router

PG_URL = "postgresql://user:pass@host:5432/db"   # plain psycopg form

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with open_graph(PG_URL) as graph:
        app.state.graph = graph
        yield

app = FastAPI(lifespan=lifespan)      # if you already have one, add lifespan= to it
app.include_router(approvals_router)