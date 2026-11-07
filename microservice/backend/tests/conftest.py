"""測試共用設定。

需要資料庫的測試使用獨立的測試資料庫（預設 chiah_ioh_lo_test，可用 TEST_DATABASE_URL 覆寫），
每個測試結束後清空資料。PostgreSQL 沒有啟動時，這些測試會略過。
"""

import asyncio
import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet

# 必須在 import app 之前設定，讓設定讀到測試用的值
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/chiah_ioh_lo_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEMO_MODE"] = "false"
os.environ.setdefault("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.db import get_session  # noqa: E402
from app.integrations.fcm.client import PushMessage  # noqa: E402
from app.main import app  # noqa: E402
from app.models import metadata  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_ACCOUNT = json.loads((REPO_ROOT / "assets" / "mock_data" / "account.json").read_text(encoding="utf-8"))["data"]

LoginFn = Callable[..., Awaitable[tuple[dict[str, str], UUID]]]


async def _prepare_database() -> bool:
    plain_url = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    server_url, db_name = plain_url.rsplit("/", 1)
    try:
        conn = await asyncpg.connect(f"{server_url}/postgres", timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name):
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        # 整個 schema 重建：資料表改名或移除後，舊表不會殘留
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(metadata.create_all)
    await engine.dispose()
    return True


@pytest.fixture(scope="session")
def database_ready() -> bool:
    return asyncio.run(_prepare_database())


@pytest_asyncio.fixture
async def sessionmaker(database_ready: bool) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if not database_ready:
        pytest.skip("需要 PostgreSQL：在 microservice/backend 執行 docker compose up -d")
    # NullPool：每個測試有自己的 event loop，連線不能跨測試共用
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        tables = ", ".join(table.name for table in metadata.sorted_tables)
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    await engine.dispose()


@pytest_asyncio.fixture
async def api(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncIterator[httpx.AsyncClient]:
    """連到測試資料庫的 API client。"""

    async def _session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


class FakePusher:
    """記下要發送的推播，取代 FCM。"""

    def __init__(self) -> None:
        self.sent: list[tuple[list[str], "PushMessage"]] = []

    async def send(self, tokens: list[str], message: "PushMessage") -> None:
        self.sent.append((tokens, message))


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> FakePusher:
    """測試中發出的推播都記在 pushes.sent。"""
    from app.modules.notification import service as notification_service

    fake = FakePusher()
    monkeypatch.setattr(notification_service, "get_pusher", lambda: fake)
    return fake


@pytest.fixture
def login(api: httpx.AsyncClient) -> LoginFn:
    """用 App 的模擬帳號（換掉 id 和姓名）登入，並選擇身分。回傳 (headers, user_id)。"""

    async def _login(townpass_id: str, name: str, role: str | None) -> tuple[dict[str, str], UUID]:
        account = {**MOCK_ACCOUNT, "id": townpass_id, "realName": name}
        resp = await api.post("/api/v1/auth/townpass", json={"name": "userinfo", "data": account})
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        if role is not None:
            assert (await api.put("/api/v1/me/role", json={"role": role}, headers=headers)).status_code == 200
        return headers, UUID(resp.json()["user"]["id"])

    return _login
