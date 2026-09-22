from __future__ import annotations

import time
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Body, HTTPException, Request

from app.config import get_settings_singleton

agentRou = APIRouter(prefix="/proxy", tags=["too-agent-proxy"])
settings = get_settings_singleton()


def _forwarded_auth_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    auth = request.headers.get("authorization")
    if auth:
        headers["authorization"] = auth
    if settings.INTERNAL_SERVICE_KEY:
        headers["X-Internal-Service-Key"] = settings.INTERNAL_SERVICE_KEY
    return headers

async def _post_to_agent(
    request: Request,
    path: str,
    body: dict[str, object],
) -> dict[str, object]:
    target_url = urljoin(str(settings.TOO_AGENT_API), path)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                target_url,
                json=body,
                headers=_forwarded_auth_headers(request),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to call TOO_AGENT_API: {exc}") from exc

    if not response.is_success:
        detail: object
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=response.status_code,
            detail={"upstream": target_url, "error": detail},
        )

    try:
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"result": data}
    except ValueError:
        return {"result": response.text}


@agentRou.get("/diagnostics")
async def diagnostics(request: Request) -> dict[str, object]:
    target_url = urljoin(str(settings.TOO_AGENT_API), "diagnose_mcp")
    caller_url = request.headers.get("origin") or request.headers.get("referer")

    agent_check: dict[str, object] = {
        "url": target_url,
        "status": "unknown",
    }
    if caller_url:
        agent_check["caller_url"] = caller_url

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(target_url, headers=_forwarded_auth_headers(request))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        agent_check["http_status"] = response.status_code
        agent_check["latency_ms"] = elapsed_ms
        agent_check["status"] = "ok" if response.is_success else "failed"
        try:
            agent_check["response"] = response.json()
        except ValueError:
            agent_check["response"] = response.text
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        agent_check["status"] = "failed"
        agent_check["latency_ms"] = elapsed_ms
        agent_check["error"] = str(exc)

    overall_status = "ok" if agent_check["status"] == "ok" else "degraded"
    return {
        "status": overall_status,
        "checks": {
            "agent": agent_check,
        },
    }


@agentRou.post("/run_tool")
async def run_tool(
    request: Request,
    body: dict[str, object] = Body(...),
) -> dict[str, object]:
    return await _post_to_agent(request, "run_tool", body)


@agentRou.post("/chat")
async def chat(
    request: Request,
    body: dict[str, object] = Body(...),
) -> dict[str, object]:
    return await _post_to_agent(request, "chat", body)


