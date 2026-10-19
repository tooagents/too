from __future__ import annotations

import asyncio
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.clients.mcp_client import MCPClient


class MCPDiagnosticService:
    def __init__(self, mcp_client: MCPClient) -> None:
        self.mcp_client = mcp_client

    async def resolve_host(self, host: str, port: int) -> list[str]:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            host,
            port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
        addresses = [str(item[4][0]) for item in infos if isinstance(item[4], tuple) and item[4]]
        return sorted(set(addresses))

    async def tcp_probe(self, host: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host=host, port=port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            return True, "tcp connect ok"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    async def diagnose(self, headers: dict[str, str] | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        parsed = urlparse(self.mcp_client.base_url)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "http"
        port = parsed.port or (443 if scheme == "https" else 80)
        steps: list[dict[str, Any]] = [
            {"step": "config", "mcp_url": self.mcp_client.base_url, "scheme": scheme, "host": host, "port": port}
        ]

        try:
            addresses = await self.resolve_host(host, port)
            steps.append({"step": "dns", "ok": True, "addresses": addresses})
        except Exception as exc:
            steps.append({"step": "dns", "ok": False, "error": f"{type(exc).__name__}: {exc}"})
            return {"ok": False, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "steps": steps}

        tcp_ok, tcp_message = await self.tcp_probe(host, port)
        steps.append({"step": "tcp", "ok": tcp_ok, "detail": tcp_message})
        if not tcp_ok:
            return {"ok": False, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "steps": steps}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                health_resp = await client.get(f"{self.mcp_client.base_url}/health")
                steps.append({"step": "http_health", "ok": True, "status_code": health_resp.status_code})
                tools = await self.mcp_client.list_tools(client, headers=headers)
                steps.append({"step": "list_tools", "ok": True, "count": len(tools)})
            except Exception as exc:
                steps.append({"step": "mcp_check", "ok": False, "error": f"{type(exc).__name__}: {exc}"})
                return {"ok": False, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "steps": steps}

        return {"ok": True, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "steps": steps}

