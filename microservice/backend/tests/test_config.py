"""部署設定：連線字串轉換、雲端啟動檢查。"""

import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings, get_settings
from app.main import create_app

GOOD = {
    "database_url": "postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/db?sslmode=require",
    "jwt_secret": "x" * 48,
    "field_encryption_key": Fernet.generate_key().decode(),
    "internal_secret": "y" * 32,
    "frontend_base_url": "https://chiah-ioh-lo.web.app",
}


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Neon：直接貼上的格式
        (
            "postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@ep-x.neon.tech/neondb?ssl=require",
        ),
        # Supabase session pooler
        (
            "postgres://postgres.abc:p@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
            "postgresql+asyncpg://postgres.abc:p@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
        ),
        # 已經是 asyncpg 格式就不動
        (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/chiah_ioh_lo",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/chiah_ioh_lo",
        ),
    ],
)
def test_database_url_normalized(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


def test_cors_origins() -> None:
    settings = Settings(frontend_base_url="https://a.web.app/", extra_cors_origins=" http://localhost:5173 , ")
    assert settings.cors_origins == ["https://a.web.app", "http://localhost:5173"]


def test_production_problems() -> None:
    assert Settings(**GOOD).production_problems() == []
    dev = Settings(_env_file=None, field_encryption_key="")
    assert len(dev.production_problems()) == 5


def test_refuses_to_start_on_render_with_dev_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("JWT_SECRET", "dev-only-change-me-at-least-32-bytes-long")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            create_app()
    finally:
        get_settings.cache_clear()


def test_starts_on_render_with_good_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER", "true")
    for key, value in GOOD.items():
        monkeypatch.setenv(key.upper(), value)
    get_settings.cache_clear()
    try:
        create_app()
    finally:
        get_settings.cache_clear()
