"""後端內建排程。"""

import asyncio
import datetime as dt
import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import clock
from app.main import create_app
from app.modules.internal import scheduler
from tests.conftest import FakePusher, LoginFn

SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
RX_1 = json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))[0]["payload"]  # 早餐飯後 08:00


def freeze(monkeypatch: pytest.MonkeyPatch, taipei: str) -> None:
    at = dt.datetime.fromisoformat(taipei).replace(tzinfo=clock.TAIPEI).astimezone(dt.UTC)
    monkeypatch.setattr(clock, "now", lambda: at)


def test_aligns_to_next_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    freeze(monkeypatch, "2026-11-05 07:59:30")
    assert scheduler.seconds_until_next_minute() == 31  # 08:00:01 執行


async def test_tick_once_sends_reminder(
    api: httpx.AsyncClient,
    login: LoginFn,
    pushes: FakePusher,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, elder_id = await login("elder-1", "陳阿嬤", "elder")
    base = f"/api/v1/elders/{elder_id}"
    await api.post("/api/v1/devices", json={"name": "push_token", "data": {"token": "elder-phone", "platform": "android"}}, headers=headers)
    qr = {"name": "qr_code_scan", "data": json.dumps(RX_1, ensure_ascii=False)}
    draft = (await api.post(f"{base}/medications/qr-preview", json=qr, headers=headers)).json()["draft"]
    await api.post(f"{base}/medications", json=draft, headers=headers)

    freeze(monkeypatch, "2026-11-05 08:00:01")
    result = await scheduler.tick_once(sessionmaker)
    assert result.created == 1
    assert pushes.sent[0][1].body.startswith("陳阿嬤，吃藥時間到囉～")


async def test_lifespan_starts_and_stops_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    started = asyncio.Event()

    async def fake_run_forever() -> None:
        started.set()
        await asyncio.Event().wait()  # 一直等到被取消

    monkeypatch.setattr(scheduler, "run_forever", fake_run_forever)
    app = create_app()
    async with app.router.lifespan_context(app):
        await asyncio.wait_for(started.wait(), timeout=1)
