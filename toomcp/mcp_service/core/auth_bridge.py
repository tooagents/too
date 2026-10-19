from functools import lru_cache

from bearerbridge import BearerBridge, BridgeSettings

from mcp_service.core.settings import load_settings


@lru_cache
def get_bridge() -> BearerBridge:
    settings = load_settings()
    return BearerBridge(
        BridgeSettings(
            jwks_url=settings.jwks_url,
            issuer=settings.jwks_iss,
            audience=settings.jwks_aud,
            algorithms=settings.jwks_algorithms,
            internal_service_key=settings.internal_service_key or None,
        )
    )
