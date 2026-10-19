from __future__ import annotations

from typing import Any

import httpx

from app.clients.mcp_client import MCPClient
from app.core.config import get_settings

_client = MCPClient(get_settings())
MCP_URL = _client.base_url


async def list_tools(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    return await _client.list_tools(client)


async def call_tool(client: httpx.AsyncClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return await _client.call_tool(client, name, arguments)
