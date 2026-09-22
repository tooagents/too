# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class _Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",extra="ignore",)

    TOO_AIVEN_ADMIN: str = ""
    TOO_AIVEN_RLS: str = ""


    TOO_SB_DB: str = "postgresql+asyncpg://username:pwd@local/icedb"
    TOO_SB_pgconn: str = ""


    DB_CONNECT_TIMEOUT_SEC: int = 10
    DB_COMMAND_TIMEOUT_SEC: int = 20
    DB_POOL_TIMEOUT_SEC: int = 10
    DB_STATEMENT_TIMEOUT_MS: int = 20000
    DB_LOCK_TIMEOUT_MS: int = 5000
    JWKS_URL: str = "https://pjenyfvefvgbldgdegxs.supabase.co/auth/v1/.well-known/jwks.json"
    JWKS_ISS: str = "https://pjenyfvefvgbldgdegxs.supabase.co/auth/v1"
    JWKS_AUD: str = "authenticated"
    JWKS_ALG: list[str] = ["ES256", "RS256"]
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    TOO_SB_RLS: str = ""
    
    OPENAI_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OCR_MODEL_ID: str = "gemini-2.5-flash"
    OCR_MAX_PAGES: int = 200
    # Pin a stable model, not the floating "*-latest" alias: the alias routes to
    # the newest preview and returns 503 "high demand" under load. gemini-3.6-flash
    # is Google's current recommended flash (2.x models now 404 as retired).
    BANK_AI_MODEL_ID: str = "gemini-3.6-flash"
    # Extra Gemini models tried (in order) if the primary keeps failing, before
    # switching providers entirely.
    BANK_AI_GEMINI_FALLBACKS: list[str] = ["gemini-3.5-flash"]
    # Per-model transient-error retries (503/429/timeout) with backoff.
    BANK_AI_MAX_RETRIES: int = 2
    # Groq — free, fast, OpenAI-compatible — is the cross-provider fallback used
    # when every Gemini attempt fails. No key => Groq step is skipped.
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL_ID: str = "llama-3.3-70b-versatile"
    # The AI model rotation ring (hard round-robin). Every AI call uses the NEXT
    # model and advances one shared global cursor, so consecutive calls never hit
    # the same model. Extend this list (to any length) to add models. Each entry is
    # "provider:model_id"; supported providers: "gemini", "groq". A model whose
    # provider has no API key is skipped.
    AI_ROTATION_MODELS: list[str] = [
        "groq:llama-3.3-70b-versatile",
        "gemini:gemini-3.6-flash",
        "gemini:gemini-3.5-flash",
    ]
    GH_OPENAI_API_KEY: str = ""
    GH_OPENAI_BASE_URL: str = "https://models.github.ai/inference"
    GH_OPENAI_MODEL_DEFAULT: str = "openai/gpt-4.1"
    
    MODEL_PRICING_JSON: str = "{\"gpt-5-mini\": {\"input\": 0.15, \"output\": 0.60}}"
    GUARDRAIL_ENABLE_LLM_JUDGE: bool = True
    PII_MINIMIZE_RAG_EVIDENCE: bool = True

    TOO_AGENT_API: str = "https://tooagent.fastapicloud.dev/"
    INTERNAL_SERVICE_KEY: str = ""

    # Brevo (transactional email) — invoice send with PDF attachment.
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = "tooagents@gmail.com"   # must be a Brevo-verified sender address
    BREVO_SENDER_NAME: str = "TooAgents"

    # ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # STRIPE_SECRET_KEY: str = ""
    # STRIPE_WEBHOOK_SECRET: str = ""
    # STRIPE_SUCCESS_URL: str = "https://t4agents.com/billing/success"
    # STRIPE_CANCEL_URL: str = "https://t4agents.com/billing/cancel"
    # STRIPE_PORTAL_RETURN_URL: str = "https://t4agents.com/billing"

    # STRIPE_PRICE_BASIC_MONTH: str= "price_1TBOWrRwLzeE6kyCNFmHZzTp"
    # STRIPE_PRICE_BASIC_YEAR: str = "price_1TBOWrRwLzeE6kyCprGxdvWK"
    # STRIPE_PRICE_PRO_MONTH: str = "price_1TBOaiRwLzeE6kyCV57uGsvn"
    # STRIPE_PRICE_PRO_YEAR: str = "price_1TBOaiRwLzeE6kyCgHUak49W"
    # STRIPE_PRICE_ENTERPRISE_MONTH: str = "price_1TBOb9RwLzeE6kyCcAgDncr1"
    # STRIPE_PRICE_ENTERPRISE_YEAR: str = "price_1TBObXRwLzeE6kyCSWexfBjm"
    
@lru_cache()
def get_settings_singleton()-> _Settings:
    return _Settings()

