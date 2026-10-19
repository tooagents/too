from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_url: str = "https://toomcp.fastapicloud.dev"
    too_sb_db: str = "postgresql+asyncpg://username:pwd@local/icedb"
    frontend_origins_raw: str = "https://t4agents.com"
    jwks_url: str = "https://pjenyfvefvgbldgdegxs.supabase.co/auth/v1/.well-known/jwks.json"
    jwks_iss: str = "https://pjenyfvefvgbldgdegxs.supabase.co/auth/v1"
    jwks_aud: str = "authenticated"
    jwks_alg_raw: str = "ES256,RS256"
    internal_service_key: str = ""

    @property
    def jwks_algorithms(self) -> tuple[str, ...]:
        return tuple(a.strip() for a in self.jwks_alg_raw.split(",") if a.strip())

    @field_validator("mcp_url")
    @classmethod
    def _normalize_mcp_url(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def frontend_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

