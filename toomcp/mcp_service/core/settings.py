from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    backend_base_url: str
    request_timeout_seconds: float
    jwks_url: str
    jwks_iss: str
    jwks_aud: str
    jwks_algorithms: tuple[str, ...]
    internal_service_key: str


def load_settings() -> Settings:
    return Settings(
        backend_base_url=os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001").rstrip("/"),
        request_timeout_seconds=float(os.getenv("MCP_REQUEST_TIMEOUT_SECONDS", "180")),
        jwks_url=os.getenv("JWKS_URL", "https://pjenyfvefvgbldgdegxs.supabase.co/auth/v1/.well-known/jwks.json"),
        jwks_iss=os.getenv("JWKS_ISS", "https://pjenyfvefvgbldgdegxs.supabase.co/auth/v1"),
        jwks_aud=os.getenv("JWKS_AUD", "authenticated"),
        jwks_algorithms=tuple(a.strip() for a in os.getenv("JWKS_ALG", "ES256,RS256").split(",") if a.strip()),
        internal_service_key=os.getenv("INTERNAL_SERVICE_KEY", ""),
    )

