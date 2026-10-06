import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.observability.http_logging import add_http_logging_middleware
from app.api import rou

logger = logging.getLogger("app.main")


def create_app() -> FastAPI:
    app = FastAPI(
        docs_url="/swagger",
        # Keep the JWT pasted in Authorize across reloads -> paste once per session.
        swagger_ui_parameters={"persistAuthorization": True},
    )

    # Middleware are applied outermost-first in REVERSE registration order, so
    # the order below is deliberate: CORS is registered last and therefore wraps
    # everything. The error handler registered first sits innermost (just above
    # the routes).

    # Innermost: convert any unhandled exception into a JSON 500 *response* here,
    # so it still travels back out through the CORS layer and gets its
    # Access-Control-Allow-Origin header. Starlette's own ServerErrorMiddleware
    # runs OUTSIDE CORS, so a 500 it produces reaches the browser header-less and
    # surfaces as a misleading "No Access-Control-Allow-Origin header" CORS error
    # that hides the real failure. The traceback is still logged below.
    @app.middleware("http")
    async def errors_as_cors_safe_json(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled error on %s %s", request.method, request.url.path
            )
            return JSONResponse(
                status_code=500, content={"detail": "Internal Server Error"}
            )

    # Request/response logging (also logs the full traceback on failure).
    add_http_logging_middleware(app)

    # Outermost: stamp CORS headers on every response passing back out, including
    # the 500s produced by the handler above.
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.ALLOWED_ORIGINS,
        # allow_credentials=True,
        allow_origins=["*"],
        allow_credentials=False,  # MUST be False when origins="*"
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(rou)

    return app
