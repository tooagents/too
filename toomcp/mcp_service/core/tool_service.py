from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException

from mcp_service.clients.backend_client import BackendClient
from mcp_service.core import tool_registry

logger = logging.getLogger(__name__)


class ToolService:
    def __init__(self, backend_client: BackendClient) -> None:
        self._backend_client = backend_client

    async def call_tool(self, name: str, arguments: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        started = time.perf_counter()

        def mark(step: str, **meta: Any) -> dict[str, Any]:
            return {
                "source": "toomcp.tool_service",
                "step": step,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                **meta,
            }

        trace: list[dict[str, Any]] = [mark("call_tool_received", tool=name, argument_keys=sorted(arguments.keys()))]
        if not tool_registry.has_tool(name):
            logger.warning(
                "call_tool unknown tool: name=%s available_tools=%s arguments=%s",
                name,
                list(tool_registry.TOOLS.keys()),
                arguments,
            )
            raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

        logger.info("call_tool start: name=%s arguments=%s", name, arguments)
        trace.append(mark("tool_lookup_ok"))

        if name == "tool1":
            result = self._tool1(arguments)
            result.setdefault("trace", trace + [mark("tool1_completed")])
            logger.info("call_tool success: name=%s result_keys=%s", name, list(result.keys()))
            return {
                "tool": name,
                "arguments": arguments,
                "result": result,
            }

        try:
            trace.append(mark("backend_invoke_start", tool=name))
            result = await self._backend_client.invoke_tool(name, arguments, headers=headers)
        except ValueError as exc:
            trace.append(mark("backend_config_error", error=str(exc)))
            logger.exception("call_tool backend config error: name=%s", name)
            raise HTTPException(status_code=500, detail={"error": str(exc), "trace": trace}) from exc
        except httpx.HTTPStatusError as exc:
            trace.append(mark("backend_http_status_error", status=exc.response.status_code, body=exc.response.text))
            logger.exception(
                "call_tool backend http status error: name=%s status=%s body=%s",
                name,
                exc.response.status_code,
                exc.response.text,
            )
            raise HTTPException(
                status_code=exc.response.status_code,
                detail={"error": "Backend returned an HTTP error", "upstream_body": exc.response.text, "trace": trace},
            ) from exc
        except httpx.HTTPError as exc:
            trace.append(mark("backend_transport_error", error_type=type(exc).__name__, error=str(exc) or repr(exc)))
            logger.exception("call_tool backend transport error: name=%s", name)
            raise HTTPException(
                status_code=502,
                detail={"error": str(exc) or repr(exc), "error_type": type(exc).__name__, "trace": trace},
            ) from exc

        if isinstance(result, dict):
            result.setdefault("trace", [])
            if isinstance(result["trace"], list):
                result["trace"] = trace + [mark("backend_invoke_done", result_keys=sorted(result.keys()))] + result["trace"]

        logger.info("call_tool success: name=%s result_keys=%s", name, list(result.keys()))
        return {
            "tool": name,
            "arguments": arguments,
            "result": result,
        }

    def _tool1(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = str(arguments.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=422, detail="tool1 requires a non-empty 'message' argument")

        return {
            "ok": True,
            "echo": message,
            "message_length": len(message),
            "handled_by": "mcp_service.core.tool_service.ToolService._tool1",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

