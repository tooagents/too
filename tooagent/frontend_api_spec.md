# Frontend API Specification

Date: 2026-05-02
Service: `app/agent_app.py`

## Base URL
- Local: `https://fastapi4toomcp.fastapicloud.dev`

## 1) GET `/`

Purpose:
- Returns `frontend/index.html`.

Input format:
- No request body.

Output format:
- Content-Type: `text/html`
- Body: HTML document

## 2) GET `/health`

Purpose:
- Health check endpoint.

Input format:
- No request body.

Output format:
- Content-Type: `application/json`
- Body:

```json
{
  "status": "ok"
}
```

## 3) POST `/chat`

Purpose:
- Unified frontend entry point for chat, direct tool execution, or plain no-tool messages.
- Requires the same auth headers as `/run_tool`; JWT/internal-service headers are forwarded to MCP calls.
- `tool_choice` controls routing:
  - `auto`: backend plans which tool to use from `arguments.message`.
  - `plain`: backend returns an answer without calling a tool.
  - any MCP tool name: backend calls that tool directly with `arguments`.
- If `tool_choice` is an unknown tool name, backend falls back to `auto`.

Input format:
- Content-Type: `application/json`
- Body:

```json
{
  "tool_choice": "auto",
  "arguments": {
    "message": "vendor: acme supplies"
  }
}
```

Fields:

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `tool_choice` | string | no | `auto` | `auto`, `plain`, or an MCP tool name like `lookup_vendor`. |
| `arguments` | object | no | `{}` | Tool arguments for direct tool calls. For `auto` and `plain`, put user text in `arguments.message`. |

Example direct tool request:

```json
{
  "tool_choice": "lookup_vendor",
  "arguments": {
    "name": "acme supplies"
  }
}
```

Example transaction-to-JE direct tool request:

```json
{
  "tool_choice": "tool_transaction2je",
  "arguments": {
    "message": "what is paris"
  }
}
```

Example plain no-tool request:

```json
{
  "tool_choice": "plain",
  "arguments": {
    "message": "hello"
  }
}
```

Output format (tool selected):
- Content-Type: `application/json`
- Body shape:

```json
{
  "answer": "string",
  "tool": "string",
  "arguments": {},
  "result": {},
  "trace": []
}
```

Example response:

```json
{
  "answer": "Vendor acme supplies is approved (low risk).",
  "tool": "lookup_vendor",
  "arguments": {
    "name": "acme supplies"
  },
  "result": {
    "name": "acme supplies",
    "category": "office",
    "risk_level": "low",
    "status": "approved"
  },
  "trace": [
    { "step": "Backend MCP client calls list_tools" }
  ]
}
```

Output format (no tool selected):

```json
{
  "answer": "No tool call needed. Try vendor/bank/ocr/tool1/tool2 patterns.",
  "trace": [
    { "step": "final_answer_without_tool" }
  ]
}
```

## 4) POST `/run_tool`

Purpose:
- Direct MCP tool execution from frontend (without message-to-tool parsing).
- Requires auth headers; JWT/internal-service headers are forwarded to MCP calls.

Input format:
- Content-Type: `application/json`
- Body:

```json
{
  "tool": "lookup_vendor",
  "arguments": {
    "name": "acme supplies"
  }
}
```

Output format:
- Content-Type: `application/json`
- Body shape:

```json
{
  "answer": "string",
  "tool": "string",
  "arguments": {},
  "result": {},
  "trace": []
}
```

## Tool Input Examples for `/run_tool`

`lookup_vendor`:

```json
{
  "tool": "lookup_vendor",
  "arguments": {
    "name": "acme supplies"
  }
}
```

`query_bank`:

```json
{
  "tool": "query_bank",
  "arguments": {
    "account_name": "ops-checking"
  }
}
```

`ocr_extract`:

```json
{
  "tool": "ocr_extract",
  "arguments": {
    "text": "invoice 1001 paid"
  }
}
```

`tool1`:

```json
{
  "tool": "tool1",
  "arguments": {
    "message": "hello"
  }
}
```

`tool2`:

```json
{
  "tool": "tool2",
  "arguments": {}
}
```

