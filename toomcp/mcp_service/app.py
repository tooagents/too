from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Match

from mcp_service.api.routes import create_router
from mcp_service.clients.backend_client import BackendClient
from mcp_service.core.settings import load_settings
from mcp_service.core.tool_service import ToolService

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = load_settings()
    backend_client = BackendClient(
        base_url=settings.backend_base_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    tool_service = ToolService(backend_client=backend_client)

    app = FastAPI(title="TooMCP Server", version="0.3.0")
    app.include_router(create_router(settings=settings, tool_service=tool_service))

    @app.on_event("startup")
    async def log_registered_routes() -> None:
        routes: list[dict[str, object]] = []
        for route in app.routes:
            if isinstance(route, APIRoute):
                routes.append(
                    {
                        "path": route.path,
                        "methods": sorted(route.methods or []),
                        "name": route.name,
                    }
                )
        logger.info("Startup route map: %s", routes)

    @app.middleware("http")
    async def log_404_diagnostics(request, call_next):
        response = await call_next(request)
        if response.status_code == 404:
            known_paths = sorted(
                {
                    route.path
                    for route in app.routes
                    if isinstance(route, APIRoute)
                }
            )
            path_matched = False
            full_matched = False
            for route in app.routes:
                match, _ = route.matches(request.scope)
                if match == Match.FULL:
                    full_matched = True
                    break
                if match == Match.PARTIAL:
                    path_matched = True

            reason = "no_route_match"
            if full_matched:
                reason = "handler_or_business_404"
            elif path_matched:
                reason = "method_not_allowed_or_partial_match"

            logger.warning(
                "404 diagnostic: reason=%s method=%s path=%s known_paths=%s",
                reason,
                request.method,
                request.url.path,
                known_paths,
            )
        return response

    return app
