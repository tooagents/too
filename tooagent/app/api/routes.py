from pathlib import Path
import json
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from app.clients.mcp_client import MCPClient
from app.core.auth_bridge import get_bridge
from app.core.config import get_settings
from app.schemas import ChatRequest, ToolRunRequest
from app.services.agent_service import AgentService
from app.services.mcp_diagnostic_service import MCPDiagnosticService

router = APIRouter()

settings = get_settings()
mcp_client = MCPClient(settings)
agent_service = AgentService(mcp_client)
diagnostic_service = MCPDiagnosticService(mcp_client)


@router.get("/")
def index() -> FileResponse:
    return FileResponse(Path("frontend") / "index.html")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/diagnose_mcp")
async def diagnose_mcp(request: Request, _: dict[str, Any] = Depends(get_bridge().require_user_and_internal_service)) -> dict[str, Any]:
    return await diagnostic_service.diagnose(get_bridge().forward_headers(request.headers))


@router.post("/chat")
async def chat(
    request: Request,
    payload: ChatRequest,
    _: dict[str, Any] = Depends(get_bridge().require_user_and_internal_service),
) -> dict[str, Any]:
    return await agent_service.chat(payload.tool_choice, payload.arguments, get_bridge().forward_headers(request.headers))


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def _chat_stream_events(request: Request, payload: ChatRequest):
    started = time.perf_counter()

    def status(step: str, **meta: object) -> str:
        return _sse(
            "status",
            {
                "source": "tooagent",
                "step": step,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "meta": meta,
            },
        )

    headers = get_bridge().forward_headers(request.headers)
    yield status(
        "request_received",
        route="/chat/stream",
        tool_choice=payload.tool_choice,
        argument_keys=sorted(payload.arguments.keys()),
    )
    yield status("chat_service_start")

    choice = (payload.tool_choice.strip() or "auto").lower()
    if choice not in {"auto", "plain"}:
        try:
            timeout = httpx.Timeout(180.0, read=None)
            async with httpx.AsyncClient(timeout=timeout) as client:
                yield status("mcp_list_tools_start")
                tools = await mcp_client.list_tools(client, headers=headers)
                available_tool_names = {tool["name"] for tool in tools}
                yield status("mcp_list_tools_response", tools=sorted(available_tool_names))

                if choice in available_tool_names:
                    yield status("direct_tool_choice", tool=choice, arguments=payload.arguments)
                    async for chunk in mcp_client.stream_call_tool(client, choice, payload.arguments, headers=headers):
                        yield chunk
                    yield status("mcp_stream_completed", tool=choice)
                    return

                yield status("unknown_tool_choice_fallback_to_chat_service", unknown_tool_choice=choice)
        except Exception as exc:
            yield _sse(
                "error",
                {
                    "source": "tooagent",
                    "step": "mcp_stream_bridge_error",
                    "message": f"{type(exc).__name__}: {exc}",
                },
            )
            return

    try:
        response = await agent_service.chat(payload.tool_choice, payload.arguments, headers)
    except Exception as exc:
        yield _sse(
            "error",
            {
                "source": "tooagent",
                "step": "chat_service_error",
                "message": f"{type(exc).__name__}: {exc}",
            },
        )
        return

    trace = response.get("trace") if isinstance(response, dict) else None
    yield status(
        "chat_service_completed",
        response_keys=sorted(response.keys()) if isinstance(response, dict) else [],
        trace_count=len(trace) if isinstance(trace, list) else 0,
    )
    yield _sse("final", {"source": "tooagent", "response": response})


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    _: dict[str, Any] = Depends(get_bridge().require_user_and_internal_service),
) -> StreamingResponse:
    return StreamingResponse(
        _chat_stream_events(request, payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/run_tool")
async def run_tool(
    request: Request,
    payload: ToolRunRequest,
    _: dict[str, Any] = Depends(get_bridge().require_user_and_internal_service),
) -> dict[str, Any]:
    return await agent_service.run_tool(payload.tool, payload.arguments, get_bridge().forward_headers(request.headers))

