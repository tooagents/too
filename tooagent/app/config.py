from app.core.config import Settings, get_settings


def get_settings_singleton() -> Settings:
    return get_settings()
