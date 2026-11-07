"""吃藥提醒：固定四個時段（09:00、12:00、18:00、22:00），長輩與家屬同時收到（UI E09、F04）。需要 PostgreSQL。"""

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import clock
from app.core.config import get_settings
from app.core.db import get_session
from app.main import create_app
from seed.load import load_licenses, sample_drug_codes
from tests.conftest import FakePusher, LoginFn

API = "/api/v1"
SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
RX_A, RX_B, RX_C = (s["payload"] for s in json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8")))


def freeze(monkeypatch: pytest.MonkeyPatch, taipei: str) -> None:
    at = dt.datetime.fromisoformat(taipei).replace(tzinfo=clock.TAIPEI).astimezone(dt.UTC)
    monkeypatch.setattr(clock, "now", lambda: at)


@pytest.fixture
async def ctx(
    api: httpx.AsyncClient, login: LoginFn, pushes: FakePusher, sessionmaker: async_sessionmaker[AsyncSession]
) -> dict:
    async with sessionmaker() as session:
        await load_licenses(session, only=sample_drug_codes())
        await session.commit()
    elder_h, elder_id = await login("elder-1", "陳阿嬤", "elder")
    family_h, _ = await login("family-1", "陳小美", "family")
    stranger_h, _ = await login("family-2", "路人", "family")
    ctx = {"elder": elder_h, "family": family_h, "stranger": stranger_h, "elder_id": elder_id}
    ctx["base"] = f"{API}/elders/{elder_id}"

    code = (await api.post(f"{API}/family/invites", headers=elder_h)).json()["code"]
    binding = await api.post(f"{API}/family/bindings", json={"code": code, "relation_label": "媽媽"}, headers=family_h)
    ctx["binding_id"] = binding.json()["id"]
    for who, token in (("elder", "elder-phone"), ("family", "daughter-phone"), ("stranger", "stranger-phone")):
        await api.post(f"{API}/devices", json={"name": "push_token", "data": {"token": token, "platform": "ios"}}, headers=ctx[who])
    return ctx


async def add(api: httpx.AsyncClient, ctx: dict, payload: dict) -> dict:
    qr = {"name": "qr_code_scan", "data": json.dumps(payload, ensure_ascii=False)}
    draft = (await api.post(f"{ctx['base']}/prescriptions/qr-preview", json=qr, headers=ctx["elder"])).json()["draft"]
    return (await api.post(f"{ctx['base']}/prescriptions", json=draft, headers=ctx["elder"])).json()["prescription"]


async def tick(api: httpx.AsyncClient) -> dict:
    resp = await api.post(f"{API}/internal/tick", headers={"X-Internal-Secret": get_settings().internal_secret})
    assert resp.status_code == 200, resp.text
    return resp.json()


def sent_to(pushes: FakePusher, token: str) -> list:
    return [message for tokens, message in pushes.sent if token in tokens]


async def test_elder_and_family_notified_at_the_same_time(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, RX_A)  # A1、A2 早上，A3 睡前
    await add(api, ctx, RX_B)  # B1 早中晚，B2 中午

    freeze(monkeypatch, "2026-11-07 11:59")
    assert (await tick(api))["created"] == 0
    freeze(monkeypatch, "2026-11-07 12:00")
    assert await tick(api) == {"created": 1, "refill": 0, "appointment": 0}

    # UI E09：長輩
    [elder] = sent_to(pushes, "elder-phone")
    assert (elder.title, elder.body) == ("中午 12:00 該吃藥了", "B1、B2 各 1 顆，點開可以聽語音")
    assert elder.data["type"] == "medication_reminder"
    assert elder.data["deeplink"].endswith(f"/reminder/{elder.data['event_id']}")
    # UI F04：家屬同時間收到（還沒建立救命卡時用台北通姓名）
    [family] = sent_to(pushes, "daughter-phone")
    assert (family.title, family.body) == ("陳阿嬤 中午 12:00 該吃藥了", "B1、B2 各 1 顆，記得關心他")
    assert family.data["type"] == "family_medication_reminder"
    assert sent_to(pushes, "stranger-phone") == []

    # 同一分鐘再跑一次不會重複；也不會再提醒
    for at in ("12:00", "12:10", "12:20", "12:30"):
        freeze(monkeypatch, f"2026-11-07 {at}")
        assert (await tick(api))["created"] == 0
    assert len(pushes.sent) == 2

    # 點開推播：時段用藥詳情，依藥單分組，朗讀不念英文字母
    screen = (await api.get(f"{API}/reminders/{elder.data['event_id']}", headers=ctx["family"])).json()
    assert (screen["label"], screen["elder_name"]) == ("中午", "陳阿嬤")
    assert [i["code"] for i in screen["items"]] == ["B1", "B2"]
    assert [g["letter"] for g in screen["groups"]] == ["B"]
    assert screen["speech_text"] == "中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆"


async def test_family_message_uses_card_name(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await api.post(f"{ctx['base']}/consents", json={}, headers=ctx["elder"])
    card = {
        "name": "王美玉",
        "birth_date": "1948-05-12",
        "gender": "female",
        "contact": {"name": "陳小華", "relation": "女兒", "phone": "0912345678"},
    }
    assert (await api.put(f"{ctx['base']}/emergency-card", json=card, headers=ctx["elder"])).status_code == 200
    await add(api, ctx, RX_A)

    freeze(monkeypatch, "2026-11-07 09:00")
    await tick(api)
    [family] = sent_to(pushes, "daughter-phone")
    assert (family.title, family.body) == ("王美玉 早上 09:00 該吃藥了", "A1、A2 各 1 顆，記得關心她")


async def test_no_late_reminder_after_30_minutes(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    await add(api, ctx, RX_A)
    freeze(monkeypatch, "2026-11-07 09:31")
    assert (await tick(api))["created"] == 0


async def test_stopped_or_finished_not_reminded(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    prescription = await add(api, ctx, RX_A)
    for med in prescription["medications"][:2]:  # 停用 A1、A2（早上），只剩 A3（睡前）
        await api.post(f"{ctx['base']}/medications/{med['id']}/stop", json={"reason": "finished"}, headers=ctx["elder"])

    freeze(monkeypatch, "2026-11-07 09:00")
    assert (await tick(api))["created"] == 0
    freeze(monkeypatch, "2026-11-07 22:00")
    assert (await tick(api))["created"] == 1
    assert sent_to(pushes, "elder-phone")[0].body == "A3 1 顆，點開可以聽語音"

    # 移到「已吃完」的藥單不再提醒
    await api.post(f"{ctx['base']}/prescriptions/{prescription['id']}/finish", headers=ctx["elder"])
    freeze(monkeypatch, "2026-11-08 22:00")
    assert (await tick(api))["created"] == 0


async def test_reminder_access_and_daily_list(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    await add(api, ctx, RX_B)
    for at in ("09:00", "12:00", "18:00"):
        freeze(monkeypatch, f"2026-11-07 {at}")
        await tick(api)

    listed = (await api.get(f"{ctx['base']}/reminders?date=2026-11-07", headers=ctx["family"])).json()
    assert [r["label"] for r in listed] == ["早上", "中午", "晚上"]
    resp = await api.get(f"{API}/reminders/{listed[0]['id']}", headers=ctx["stranger"])
    assert resp.json()["error"]["code"] == "NOT_BOUND"


async def test_nudge(api: httpx.AsyncClient, ctx: dict, pushes: FakePusher) -> None:
    assert (await api.post(f"{ctx['base']}/nudge", headers=ctx["family"])).status_code == 204
    assert sent_to(pushes, "elder-phone")[0].body == "陳小美提醒你吃藥喔"
    resp = await api.post(f"{ctx['base']}/nudge", headers=ctx["elder"])
    assert resp.json()["error"]["code"] == "FAMILY_ONLY"


async def test_refill_reminder(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, RX_A)  # 11/05 起 28 天，12/02 吃完

    freeze(monkeypatch, "2026-11-25 08:59")
    assert (await tick(api))["refill"] == 0
    freeze(monkeypatch, "2026-11-25 09:00")
    assert (await tick(api))["refill"] == 1
    text = "藥單 A（仁愛院區 心臟內科）再 7 天就吃完囉，要記得回診或領慢箋"
    refill = [m for m in sent_to(pushes, "elder-phone") if m.data["type"] == "refill_reminder"]
    assert [m.body for m in refill] == [text]
    assert any(m.body == text for m in sent_to(pushes, "daughter-phone"))
    # 同一個吃完日只發一次
    freeze(monkeypatch, "2026-11-25 10:00")
    assert (await tick(api))["refill"] == 0


async def test_tick_requires_secret(api: httpx.AsyncClient) -> None:
    assert (await api.post(f"{API}/internal/tick", headers={"X-Internal-Secret": "wrong"})).status_code == 401


# ---------- Demo 觸發（只在 DEMO_MODE） ----------


@pytest.fixture
async def demo_api(
    monkeypatch: pytest.MonkeyPatch, sessionmaker: async_sessionmaker[AsyncSession]
) -> httpx.AsyncClient:
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    app = create_app()

    async def _session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
    monkeypatch.delenv("DEMO_MODE")
    get_settings.cache_clear()


async def test_demo_triggers(
    api: httpx.AsyncClient, ctx: dict, demo_api: httpx.AsyncClient, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze(monkeypatch, "2026-11-07 15:00")
    await add(api, ctx, RX_A)
    query = f"?elder_id={ctx['elder_id']}"

    # 今天第一個有藥的時段（早上），長輩與家屬同時收到；再按一次會再推播
    for _ in range(2):
        resp = await demo_api.post(f"{API}/demo/trigger/reminder{query}", headers=ctx["family"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["label"] == "早上"
    assert [m.title for m in sent_to(pushes, "elder-phone")] == ["早上 09:00 該吃藥了"] * 2
    assert len(sent_to(pushes, "daughter-phone")) == 2

    resp = await demo_api.post(f"{API}/demo/trigger/refill{query}", headers=ctx["family"])
    assert resp.json() == {"letters": ["A"]}

    # 一般模式沒有 demo API
    assert (await api.post(f"{API}/demo/trigger/refill{query}", headers=ctx["family"])).status_code == 404
