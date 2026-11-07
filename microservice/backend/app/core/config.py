import os
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-change-me-at-least-32-bytes-long"
DEV_INTERNAL_SECRET = "dev-internal-secret"

# Neon、Supabase 連線字串中 asyncpg 看不懂的參數
_LIBPQ_ONLY_PARAMS = {"channel_binding", "options", "target_session_attrs"}


class Settings(BaseSettings):
    """環境變數設定，說明見 docs/backend-spec.md §10。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 可以直接貼上 Neon、Supabase 提供的 postgresql://…?sslmode=require，會自動轉成 asyncpg 格式
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chiah_ioh_lo"

    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    user_token_ttl_hours: int = 24 * 7
    responder_token_ttl_hours: int = 12

    # Fernet 金鑰；產生方式：uv run python -m scripts.gen_secrets
    # 加密的個資只能用同一把金鑰解開，部署後不可更換、不可遺失
    field_encryption_key: str = ""

    # Firebase 服務帳戶金鑰：JSON 檔路徑，或直接貼上 JSON 內容；留空表示推播只寫 log
    firebase_credentials: str | None = None
    internal_secret: str = DEV_INTERNAL_SECRET
    frontend_base_url: str = "http://localhost:5173"
    # 額外允許呼叫 API 的網頁來源，逗號分隔；例如前端在本機開發時連雲端後端：http://localhost:5173
    extra_cors_origins: str = ""
    remind_interval_minutes: int = 10
    demo_mode: bool = False

    @field_validator("database_url")
    @classmethod
    def _to_asyncpg(cls, url: str) -> str:
        """postgresql://…?sslmode=require → postgresql+asyncpg://…?ssl=require"""
        parts = urlsplit(url)
        scheme = parts.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+asyncpg"
        query = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if key == "sslmode":
                key, value = "ssl", value
            if key not in _LIBPQ_ONLY_PARAMS:
                query.append((key, value))
        return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    @property
    def cors_origins(self) -> list[str]:
        extra = [o.strip().rstrip("/") for o in self.extra_cors_origins.split(",") if o.strip()]
        return [self.frontend_base_url.rstrip("/"), *extra]

    @property
    def on_cloud(self) -> bool:
        """在雲端主機上執行（Render 會自動設定 RENDER，Cloud Run 會設定 K_SERVICE）。"""
        return "RENDER" in os.environ or "K_SERVICE" in os.environ

    def production_problems(self) -> list[str]:
        """部署到雲端時不可使用的開發設定。"""
        problems = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET 還是開發用的預設值或太短")
        if not self.field_encryption_key:
            problems.append("沒有設定 FIELD_ENCRYPTION_KEY")
        if self.internal_secret == DEV_INTERNAL_SECRET:
            problems.append("INTERNAL_SECRET 還是開發用的預設值")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            problems.append("DATABASE_URL 指向 localhost")
        if "localhost" in self.frontend_base_url:
            problems.append("FRONTEND_BASE_URL 指向 localhost")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
