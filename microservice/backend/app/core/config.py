from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境變數設定，說明見 docs/backend-spec.md §10。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chiah_ioh_lo"

    jwt_secret: str = "dev-only-change-me-at-least-32-bytes-long"
    jwt_algorithm: str = "HS256"
    user_token_ttl_hours: int = 24 * 7
    responder_token_ttl_hours: int = 12

    # Fernet 金鑰；產生方式：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    field_encryption_key: str = ""

    firebase_credentials: str | None = None
    internal_secret: str = "dev-internal-secret"
    frontend_base_url: str = "http://localhost:5173"
    remind_interval_minutes: int = 10
    demo_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
