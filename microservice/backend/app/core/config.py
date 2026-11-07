from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 一般 PostgreSQL 連線字串中 asyncpg 看不懂的參數
_LIBPQ_ONLY_PARAMS = {"channel_binding", "options", "target_session_attrs"}


class Settings(BaseSettings):
    """環境變數設定（.env），說明見 docs/backend-spec.md §10。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 一般的 postgresql://… 也可以，會自動轉成 asyncpg 格式
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chiah_ioh_lo"

    jwt_secret: str = "dev-only-change-me-at-least-32-bytes-long"
    jwt_algorithm: str = "HS256"
    user_token_ttl_hours: int = 24 * 7
    responder_token_ttl_hours: int = 12

    # Fernet 金鑰，由 uv run python -m scripts.init_env 產生
    # 加密的個資只能用同一把金鑰解開，開始存資料後不可更換、不可遺失
    field_encryption_key: str = ""

    # Firebase 服務帳戶金鑰：JSON 檔路徑，或直接貼上 JSON 內容；留空表示推播只寫 log
    firebase_credentials: str | None = None
    internal_secret: str = "dev-internal-secret"

    # 前端網址：CORS、推播連結、救命卡與邀請 QR。Android 模擬器連電腦本機要用 10.0.2.2
    frontend_base_url: str = "http://10.0.2.2:5173"
    # 額外允許呼叫 API 的網頁來源，逗號分隔；例如在電腦瀏覽器開前端：http://localhost:5173
    extra_cors_origins: str = "http://localhost:5173"

    # 後端內建排程：每分鐘檢查吃藥提醒、回診與預約提醒
    scheduler_enabled: bool = True
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
