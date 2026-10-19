from __future__ import annotations

import logging
import json
from typing import Any
from collections.abc import AsyncIterator

import httpx

from app.core.config import Settings

logger = logging.getLogger("mcp_client")


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


class MCPClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.mcp_url

    async def list_tools(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/list_tools"
        resp = await client.get(url, headers=headers)
        logger.info("MCP list_tools status=%s", resp.status_code)
        resp.raise_for_status()
        return resp.json()["tools"]

    async def call_tool(
        self,
        client: httpx.AsyncClient,
        name: str,
        arguments: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/call_tool"
        resp = await client.post(url, json={"name": name, "arguments": arguments}, headers=headers)
        logger.info("MCP call_tool status=%s tool=%s", resp.status_code, name)
        resp.raise_for_status()
        return resp.json()["result"]

    async def stream_call_tool(
        self,
        client: httpx.AsyncClient,
        name: str,
        arguments: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[str]:
        url = f"{self.base_url}/call_tool/stream"
        async with client.stream(
            "POST",
            url,
            json={"name": name, "arguments": arguments},
            headers={**(headers or {}), "accept": "text/event-stream"},
        ) as resp:
            logger.info("MCP stream call_tool status=%s tool=%s", resp.status_code, name)
            content_type = resp.headers.get("content-type", "")
            if not resp.is_success:
                body = await resp.aread()
                yield _sse(
                    "error",
                    {
                        "source": "tooagent.mcp_client",
                        "step": "mcp_stream_http_error",
                        "status": resp.status_code,
                        "body": body.decode("utf-8", errors="replace"),
                    },
                )
                return

            if "text/event-stream" not in content_type:
                body = await resp.aread()
                yield _sse(
                    "error",
                    {
                        "source": "tooagent.mcp_client",
                        "step": "mcp_stream_not_available",
                        "status": resp.status_code,
                        "body": body.decode("utf-8", errors="replace"),
                    },
                )
                return

            async for chunk in resp.aiter_text():
                if chunk:
                    yield chunk

