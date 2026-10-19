from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BackendClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            if tool_name == "lookup_vendor":
                return await self._get(client, "/too/mcp/vendors/lookup", {"name": str(arguments.get("name", ""))}, headers=headers)

            if tool_name == "query_bank":
                return await self._get(
                    client,
                    "/bank/query",
                    {"account_name": str(arguments.get("account_name", ""))},
                    headers=headers,
                )

            if tool_name == "ocr_extract":
                return await self._post(client, "/ocr/extract", {"text": str(arguments.get("text", ""))}, headers=headers)

            if tool_name == "tool2":
                upstream = await self._get(client, "/health", {}, headers=headers)
                return {
                    "ok": True,
                    "backend_base_url": self._base_url,
                    "upstream": upstream,
                }

            if tool_name == "tool_transaction2je":
                return await self._post(
                    client,
                    "/too/mcpcallback/transaction2je",
                    {"message": str(arguments.get("message", ""))},
                    headers=headers,
                )

            raise ValueError(f"Backend forwarding is not configured for tool: {tool_name}")

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        request = client.build_request("GET", url, params=params, headers=headers)
        started = time.perf_counter()
        logger.info("Backend request: method=%s url=%s", request.method, request.url)
        response = await client.send(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info("Backend response: method=%s url=%s status=%s", request.method, request.url, response.status_code)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            data.setdefault(
                "trace",
                [],
            )
            if isinstance(data["trace"], list):
                data["trace"].insert(
                    0,
                    {
                        "source": "toomcp.backend_client",
                        "step": "backend_get_response",
                        "method": request.method,
                        "path": path,
                        "status": response.status_code,
                        "elapsed_ms": elapsed_ms,
                    },
                )
        return data

    async def _post(
        self,
        client: httpx.AsyncClient,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        request = client.build_request("POST", url, json=payload, headers=headers)
        started = time.perf_counter()
        logger.info("Backend request: method=%s url=%s", request.method, request.url)
        response = await client.send(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info("Backend response: method=%s url=%s status=%s", request.method, request.url, response.status_code)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            data.setdefault("trace", [])
            if isinstance(data["trace"], list):
                data["trace"].insert(
                    0,
                    {
                        "source": "toomcp.backend_client",
                        "step": "backend_post_response",
                        "method": request.method,
                        "path": path,
                        "status": response.status_code,
                        "elapsed_ms": elapsed_ms,
                    },
                )
        return data

