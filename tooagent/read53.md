# read53 - Frontend Kept, MCP Split Out

Date: 2026-05-02

## Goal
- Keep this service as the frontend-facing runtime (serves `frontend/index.html` and API endpoints).
- Split MCP communication logic into a separate module so MCP concerns are isolated.
- Leave existing README files unchanged.

## What Changed
- Kept frontend hard mount in `app/agent_app.py`:
  - `app.mount("/static", StaticFiles(directory="frontend"), name="static")`
  - `GET /` still returns `frontend/index.html`.
- Moved MCP HTTP calls out of `agent_app.py` into `app/mcp_client.py`:
  - `list_tools(client)` -> calls `GET {MCP_URL}/list_tools`
  - `call_tool(client, name, arguments)` -> calls `POST {MCP_URL}/call_tool`
- Updated `app/agent_app.py` to use `app.mcp_client` in `/run_tool`.

## Current Service Responsibilities
- Terminal 1 (this repo/service):
  - Serves frontend page and static assets.
  - Accepts user/API requests (`/chat`, `/run_tool`).
  - Calls MCP server using `MCP_URL`.
- Terminal 2:
  - Frontend handled separately by your team.
- Terminal 3:
  - MCP server handled separately by your team.

## Config
- `MCP_URL` (default: `http://127.0.0.1:8002`)
- `FRONTEND_ORIGINS` (comma-separated, CORS allowlist)

## Why This Helps
- Cleaner boundaries: agent runtime logic stays in `agent_app`, MCP transport logic stays in `mcp_client`.
- Easier future changes: retry/auth/logging for MCP calls can be added in one place.
