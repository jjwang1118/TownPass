"""設定：連線字串轉換、CORS 來源、本地部署預設值。"""

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:p@db.example.com/mydb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@db.example.com/mydb?ssl=require",
        ),
        (
            "postgres://postgres:postgres@db:5432/chiah_ioh_lo",
            "postgresql+asyncpg://postgres:postgres@db:5432/chiah_ioh_lo",
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
    settings = Settings(frontend_base_url="http://10.0.2.2:5173/", extra_cors_origins=" http://localhost:5173 , ")
    assert settings.cors_origins == ["http://10.0.2.2:5173", "http://localhost:5173"]


def test_local_defaults_for_android_emulator() -> None:
    """Android 模擬器裡的 App 用 10.0.2.2 連到電腦本機。"""
    settings = Settings(_env_file=None)
    assert settings.frontend_base_url == "http://10.0.2.2:5173"
    assert "http://localhost:5173" in settings.cors_origins
    assert settings.scheduler_enabled is True
