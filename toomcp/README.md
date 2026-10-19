# TooMCP (MCP Service Repo)

This repository is now MCP-focused and ready to deploy as:

- `https://toomcp.fastapicloud.com`

## Current repo layout

- MCP service (active): `mcp_server.py`, `main.py`, `mcp_service/`
- Frontend (kept for migration): `frontend/`
- Backend code + DB demo artifacts (kept for migration): `backend/`

## MCP API

- `GET /health` -> health check
- `GET /config` -> runtime config (backend URL, timeout, tools)
- `GET /list_tools` -> available tools and schemas
- `POST /call_tool` -> execute tool and return result

## Tools

### Backend-forwarded tools

- `lookup_vendor(name)` -> `GET {BACKEND_BASE_URL}/vendors/lookup`
- `query_bank(account_name)` -> `GET {BACKEND_BASE_URL}/bank/query`
- `ocr_extract(text)` -> `POST {BACKEND_BASE_URL}/ocr/extract`
- `tool2()` -> `GET {BACKEND_BASE_URL}/health` and returns wrapped backend status
- `tool_transaction2je(message)` -> `POST {BACKEND_BASE_URL}/accounting/post-transaction-journal-entry`

### MCP-native tool

- `tool1(message)` -> handled inside MCP (`ToolService._tool1`), no backend call.

Example (`tool1`):

```bash
curl -X POST http://127.0.0.1:8002/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name":"tool1","arguments":{"message":"hello mcp"}}'
```

Example (`tool2`):

```bash
curl -X POST http://127.0.0.1:8002/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name":"tool2","arguments":{}}'
```

Example (`tool_transaction2je`):

```bash
curl -X POST http://127.0.0.1:8002/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool_choice":"tool_transaction2je","arguments":{"message":"Uber $25 today"}}'
```

This tool is intentionally backend-forwarded. The backend should own any OpenAI call, schema/account mapping, validation, and database posting for the accounting workflow.

## How to add more tools

1. Add tool metadata + input schema in `mcp_service/core/tool_registry.py`.
2. Choose execution style:
   - MCP-native logic: implement a method in `mcp_service/core/tool_service.py` and branch in `call_tool()`.
   - Backend-forwarded: add explicit dispatch in `mcp_service/clients/backend_client.py`.
3. Keep route layer unchanged (`mcp_service/api/routes.py`) unless API contract changes.

## Environment variables

Copy `.env.example` and set values in your deployment platform:

- `BACKEND_BASE_URL` (required in production): backend domain/base URL
- `MCP_REQUEST_TIMEOUT_SECONDS` (optional, default `15`)

Example production value:

- `BACKEND_BASE_URL=https://your-backend-domain.com`

## Run MCP locally

```bash
uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 8002
```

## Notes for your split

- You can move `frontend/` into your frontend project.
- You can move `backend/` into your backend project.
- This repo can remain MCP-only after you complete those moves.
