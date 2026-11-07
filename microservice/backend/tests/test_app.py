"""不需要資料庫的 API 測試：路由、錯誤格式、認證。"""

import httpx
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.main import app
from app.models import metadata


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_healthz(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"status": "ok"}


async def test_requires_login(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


async def test_validation_error_format(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/townpass", json={"name": "userinfo", "data": []})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_common_items(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/emergency-card/common-items")
    assert resp.status_code == 200
    assert "高血壓" in resp.json()["chronic_conditions"]


async def test_internal_tick_requires_secret(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/v1/internal/tick")).status_code == 401


def test_schema_compiles_for_postgresql() -> None:
    """沒有資料庫時，至少確認每張表與索引都能編譯成 PostgreSQL DDL。"""
    dialect = postgresql.dialect()
    for table in metadata.sorted_tables:
        str(CreateTable(table).compile(dialect=dialect))
        for index in table.indexes:
            str(CreateIndex(index).compile(dialect=dialect))
    assert len(metadata.tables) == 20
