# Tiny MCP Flow Demo (React/FastAPI/DB/MCP/Agent)

This repo is a minimal working demo of the exact flow in your original sketch:

User -> Frontend -> Agent Runtime -> MCP `list_tools` -> LLM picks tool -> MCP `call_tool` -> MCP server tool function -> Backend API/DB -> result back -> Agent final answer -> Frontend -> User.

## What is included

- Frontend chat UI: `frontend/index.html`
- Agent runtime + MCP client: `app/agent_app.py`
- MCP server (separate process): `mcp_server.py`
- External backend API (separate process): `app/external_api.py`
- SQLite DB + seed data: `app/db.py`, `data/demo.db`
- Terminal demonstration script: `demo_flow.py`

## Tool contracts in MCP server

- `lookup_vendor(name)` -> calls backend `/vendors/lookup`
- `query_bank(account_name)` -> calls backend `/bank/query`
- `ocr_extract(text)` -> calls backend `/ocr/extract`

## Run locally

Install dependencies:

```bash
uv sync
```

Start backend API (Terminal 1):

```bash
uv run uvicorn app.external_api:app --host 127.0.0.1 --port 8001
```

Start MCP server (Terminal 2):

```bash
uv run uvicorn mcp_server:app --host 127.0.0.1 --port 8002
```

Start frontend + agent runtime (Terminal 3):

```bash
uv run uvicorn app.agent_app:app --host 127.0.0.1 --port 8000
```

Open:

- http://127.0.0.1:8000

Try messages:

- `vendor: acme supplies`
- `bank: ops-checking`
- `ocr: invoice 1001 paid`

## Demonstrate each README step in terminal

With all 3 services running:

```bash
uv run python demo_flow.py
```

It prints each stage of the loop plus the final answer and raw trace JSON.

## Notes

- The "LLM decides tool call" step is represented by a deterministic selector in `choose_tool()` for a reproducible demo.
- You can later swap that selector for real OpenAI function/tool calling while keeping the MCP/Backend shape unchanged.
