from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import httpx

from mcp_service.core.auth_bridge import get_bridge
from mcp_service.core.settings import Settings
from mcp_service.core import tool_registry
from mcp_service.core.tool_service import ToolService
from mcp_service.models.schemas import ToolCallRequest

logger = logging.getLogger(__name__)


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def create_router(settings: Settings, tool_service: ToolService) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/config")
    def config(_: dict[str, object] = Depends(get_bridge().require_user_and_internal_service)) -> dict[str, object]:
        return {
            "backend_base_url": settings.backend_base_url,
            "request_timeout_seconds": settings.request_timeout_seconds,
            "tools": list(tool_registry.TOOLS.keys()),
        }

    @router.get("/list_tools")
    def list_tools(_: dict[str, object] = Depends(get_bridge().require_user_and_internal_service)) -> dict[str, object]:
        return {"tools": tool_registry.list_tool_descriptors()}

    @router.post("/call_tool")
    async def call_tool(
        request: Request,
        payload: ToolCallRequest,
        _: dict[str, object] = Depends(get_bridge().require_user_and_internal_service),
    ) -> dict[str, object]:
        logger.info(
            "HTTP /call_tool payload: name=%s argument_keys=%s",
            payload.tool_name,
            sorted(payload.arguments.keys()),
        )
        return await tool_service.call_tool(
            name=payload.tool_name,
            arguments=payload.arguments,
            headers=get_bridge().forward_headers(request.headers),
        )

    @router.post("/call_tool/stream")
    async def call_tool_stream(
        request: Request,
        payload: ToolCallRequest,
        _: dict[str, object] = Depends(get_bridge().require_user_and_internal_service),
    ) -> StreamingResponse:
        async def events():
            started = time.perf_counter()
            tool_name = payload.tool_name

            def status(step: str, **meta: object) -> str:
                return _sse(
                    "status",
                    {
                        "source": "toomcp",
                        "step": step,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                        "meta": meta,
                    },
                )

            yield status(
                "call_tool_request_received",
                tool=tool_name,
                argument_keys=sorted(payload.arguments.keys()),
            )

            if not tool_registry.has_tool(tool_name):
                yield _sse("error", {"source": "toomcp", "step": "unknown_tool", "tool": tool_name})
                return

            backend_path = None
            if tool_name == "tool_transaction2je":
                backend_path = "/too/mcpcallback/transaction2je"
            elif tool_name == "lookup_vendor":
                backend_path = "/too/mcp/vendors/lookup"
            elif tool_name == "query_bank":
                backend_path = "/bank/query"
            elif tool_name == "ocr_extract":
                backend_path = "/ocr/extract"
            elif tool_name == "tool2":
                backend_path = "/health"

            yield status("tool_lookup_ok", tool=tool_name)
            if backend_path:
                yield status(
                    "backend_invoke_start",
                    tool=tool_name,
                    backend_base_url=settings.backend_base_url,
                    backend_path=backend_path,
                    timeout_seconds=settings.request_timeout_seconds,
                )

            if tool_name == "tool_transaction2je":
                stream_path = "/too/mcpcallback/transaction2je/stream"
                url = f"{settings.backend_base_url}{stream_path}"
                yield status("backend_stream_start", tool=tool_name, backend_path=stream_path)
                try:
                    timeout = httpx.Timeout(settings.request_timeout_seconds, read=None)
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream(
                            "POST",
                            url,
                            json={"message": str(payload.arguments.get("message", ""))},
                            headers={
                                **get_bridge().forward_headers(request.headers),
                                "accept": "text/event-stream",
                            },
                        ) as response:
                            content_type = response.headers.get("content-type", "")
                            yield status(
                                "backend_stream_headers",
                                http_status=response.status_code,
                                content_type=content_type,
                            )
                            if not response.is_success:
                                body = await response.aread()
                                yield _sse(
                                    "error",
                                    {
                                        "source": "toomcp",
                                        "step": "backend_stream_http_error",
                                        "status_code": response.status_code,
                                        "body": body.decode("utf-8", errors="replace"),
                                    },
                                )
                                return
                            if "text/event-stream" not in content_type:
                                body = await response.aread()
                                yield _sse(
                                    "error",
                                    {
                                        "source": "toomcp",
                                        "step": "backend_stream_not_sse",
                                        "status_code": response.status_code,
                                        "body": body.decode("utf-8", errors="replace"),
                                    },
                                )
                                return

                            async for chunk in response.aiter_text():
                                if chunk:
                                    yield chunk
                    yield status("backend_stream_completed", tool=tool_name)
                    return
                except Exception as exc:
                    yield _sse(
                        "error",
                        {
                            "source": "toomcp",
                            "step": "backend_stream_exception",
                            "message": f"{type(exc).__name__}: {exc}",
                        },
                    )
                    return

            task = asyncio.create_task(
                tool_service.call_tool(
                    name=tool_name,
                    arguments=payload.arguments,
                    headers=get_bridge().forward_headers(request.headers),
                )
            )

            heartbeat = 0
            while not task.done():
                await asyncio.sleep(3)
                heartbeat += 1
                yield status(
                    "backend_invoke_waiting" if backend_path else "tool_execution_waiting",
                    heartbeat=heartbeat,
                    tool=tool_name,
                    backend_path=backend_path,
                )

            try:
                result = task.result()
            except HTTPException as exc:
                yield _sse(
                    "error",
                    {
                        "source": "toomcp",
                        "step": "call_tool_http_exception",
                        "status_code": exc.status_code,
                        "detail": exc.detail,
                    },
                )
                return
            except Exception as exc:
                yield _sse(
                    "error",
                    {
                        "source": "toomcp",
                        "step": "call_tool_exception",
                        "message": f"{type(exc).__name__}: {exc}",
                    },
                )
                return

            yield status(
                "call_tool_completed",
                tool=tool_name,
                result_keys=sorted(result.keys()) if isinstance(result, dict) else [],
            )
            yield _sse("final", {"source": "toomcp", "response": result})

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router

