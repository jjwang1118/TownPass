"""吃藥提醒：功能規格 1-5、1-6、3-1。需要 PostgreSQL。

用固定時間模擬排程：08:00 提醒 → 08:10、08:20 再提醒 → 08:30 通知家人沒有回應。
"""

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
from tests.conftest import FakePusher, LoginFn

API = "/api/v1"
SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
AMLODIPINE_5, METFORMIN, AMLODIPINE_10 = (
    s["payload"] for s in json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))
)
ELDER_PHONE = "0932166777"  # assets/mock_data/account.json 的 phoneNo


def freeze(monkeypatch: pytest.MonkeyPatch, taipei: str) -> None:
    at = dt.datetime.fromisoformat(taipei).replace(tzinfo=clock.TAIPEI).astimezone(dt.UTC)
    monkeypatch.setattr(clock, "now", lambda: at)


@pytest.fixture
async def ctx(api: httpx.AsyncClient, login: LoginFn, pushes: FakePusher) -> dict:
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
    draft = (await api.post(f"{ctx['base']}/medications/qr-preview", json=qr, headers=ctx["elder"])).json()["draft"]
    return (await api.post(f"{ctx['base']}/medications", json=draft, headers=ctx["elder"])).json()["medication"]


async def tick(api: httpx.AsyncClient) -> dict:
    resp = await api.post(f"{API}/internal/tick", headers={"X-Internal-Secret": get_settings().internal_secret})
    assert resp.status_code == 200, resp.text
    return resp.json()


def sent_to(pushes: FakePusher, token: str) -> list:
    return [message for tokens, message in pushes.sent if token in tokens]


# ---------- 1-5 吃藥提醒畫面 ----------


async def test_remind_at_slot_time(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, AMLODIPINE_5)  # 1 號：早餐飯後
    await add(api, ctx, METFORMIN)  # 2 號：早餐飯後、晚餐飯後

    freeze(monkeypatch, "2026-11-05 07:59")
    assert (await tick(api))["created"] == 0

    freeze(monkeypatch, "2026-11-05 08:00")
    assert (await tick(api))["created"] == 1
    [message] = sent_to(pushes, "elder-phone")
    assert message.body == "陳阿嬤，吃藥時間到囉～飯後吃：1 號 1 顆、2 號 1 顆"
    assert message.data["type"] == "medication_reminder"
    assert message.data["deeplink"].endswith(f"/reminder/{message.data['event_id']}")
    assert sent_to(pushes, "daughter-phone") == []  # 家人不會每個時段都收到

    # 同一分鐘再跑一次不會重複
    assert await tick(api) == {"created": 0, "repushed": 0, "escalated": 0, "refill": 0}

    # 提醒畫面：大字顯示「1 號 → 1 顆」，並朗讀
    screen = (await api.get(f"{API}/reminders/{message.data['event_id']}", headers=ctx["elder"])).json()
    assert [(i["number"], i["qty"]) for i in screen["items"]] == [(1, 1), (2, 1)]
    assert screen["label"] == "早餐飯後"
    assert screen["speech_text"] == message.body
    assert screen["status"] == "pending"


async def test_speech_uses_card_title_and_skips_latin(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, AMLODIPINE_10)  # 半顆
    await api.post(f"{ctx['base']}/consents", json={}, headers=ctx["elder"])
    await api.put(f"{ctx['base']}/emergency-card", json={"title": "阿嬤", "gender": "female"}, headers=ctx["elder"])

    freeze(monkeypatch, "2026-11-05 08:00")
    await tick(api)
    assert sent_to(pushes, "elder-phone")[0].body == "阿嬤，吃藥時間到囉～飯後吃：1 號 半顆"


async def test_no_late_reminder_after_30_minutes(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    await add(api, ctx, AMLODIPINE_5)
    freeze(monkeypatch, "2026-11-05 08:30")  # 排程延誤 30 分鐘
    assert (await tick(api))["created"] == 0


async def test_no_duplicate_after_time_change(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    await add(api, ctx, AMLODIPINE_5)
    freeze(monkeypatch, "2026-11-05 08:00")
    assert (await tick(api))["created"] == 1
    slot = {"slots": [{"slot_key": "breakfast_after", "time": "08:15"}]}
    await api.put(f"{ctx['base']}/time-slots", json=slot, headers=ctx["elder"])
    freeze(monkeypatch, "2026-11-05 08:15")
    assert (await tick(api))["created"] == 0
    # 隔天照新的時間提醒
    freeze(monkeypatch, "2026-11-06 08:15")
    assert (await tick(api))["created"] == 1


async def test_stopped_or_finished_medication_not_reminded(
    api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    med = await add(api, ctx, AMLODIPINE_5)  # 11/01～11/28
    freeze(monkeypatch, "2026-11-29 08:00")
    assert (await tick(api))["created"] == 0  # 已吃完
    freeze(monkeypatch, "2026-11-05 08:00")
    await api.post(f"{ctx['base']}/medications/{med['id']}/stop", json={"reason": "doctor_advised"}, headers=ctx["elder"])
    assert (await tick(api))["created"] == 0  # 已停用


# ---------- 1-6 沒回應：再提醒 3 次後通知家人 ----------


async def test_no_response_flow(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, AMLODIPINE_5)
    await api.post(f"{ctx['base']}/consents", json={}, headers=ctx["elder"])
    await api.put(f"{ctx['base']}/emergency-card", json={"title": "陳阿嬤", "gender": "female"}, headers=ctx["elder"])

    timeline = [
        ("08:00", {"created": 1}),
        ("08:09", {}),
        ("08:10", {"repushed": 1}),  # 第 2 次
        ("08:20", {"repushed": 1}),  # 第 3 次
        ("08:29", {}),
        ("08:30", {"escalated": 1}),  # 通知家人
        ("08:40", {}),  # 之後不再推播
    ]
    for hhmm, expected in timeline:
        freeze(monkeypatch, f"2026-11-05 {hhmm}")
        assert await tick(api) == {"created": 0, "repushed": 0, "escalated": 0, "refill": 0, **expected}, hhmm

    assert len(sent_to(pushes, "elder-phone")) == 3
    [message] = sent_to(pushes, "daughter-phone")
    assert message.body == "媽媽 08:00 的吃藥提醒沒有回應，要不要打給她？"
    assert message.data["type"] == "medication_no_response"
    assert json.loads(message.data["call"]) == {"name": "phone_call", "data": ELDER_PHONE}
    assert sent_to(pushes, "stranger-phone") == []

    screen = (await api.get(f"{API}/reminders/{message.data['event_id']}", headers=ctx["family"])).json()
    assert (screen["status"], screen["attempts"]) == ("no_response", 3)


async def test_ack(api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch) -> None:
    await add(api, ctx, AMLODIPINE_5)
    freeze(monkeypatch, "2026-11-05 08:00")
    await tick(api)
    event_id = sent_to(pushes, "elder-phone")[0].data["event_id"]
    url = f"{API}/reminders/{event_id}/ack"

    # 只有長輩本人可以按「好，我知道了」
    assert (await api.post(url, headers=ctx["family"])).json()["error"]["code"] == "ELDER_ONLY"

    freeze(monkeypatch, "2026-11-05 08:03")
    assert (await api.post(url, headers=ctx["elder"])).json()["status"] == "acked"
    [message] = sent_to(pushes, "daughter-phone")
    assert message.body == "媽媽已回應 08:00 的吃藥提醒"
    assert message.data["type"] == "medication_acked"

    # 重複按不會重複通知；回應後不再提醒
    await api.post(url, headers=ctx["elder"])
    assert len(sent_to(pushes, "daughter-phone")) == 1
    freeze(monkeypatch, "2026-11-05 08:30")
    assert await tick(api) == {"created": 0, "repushed": 0, "escalated": 0, "refill": 0}


async def test_ack_notification_can_be_turned_off(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await api.patch(f"{API}/family/bindings/{ctx['binding_id']}", json={"notify_on_ack": False}, headers=ctx["family"])
    await add(api, ctx, AMLODIPINE_5)
    freeze(monkeypatch, "2026-11-05 08:00")
    await tick(api)
    event_id = sent_to(pushes, "elder-phone")[0].data["event_id"]
    await api.post(f"{API}/reminders/{event_id}/ack", headers=ctx["elder"])
    assert sent_to(pushes, "daughter-phone") == []


async def test_reminder_access_and_daily_list(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, METFORMIN)
    for hhmm in ("08:00", "18:00"):
        freeze(monkeypatch, f"2026-11-05 {hhmm}")
        await tick(api)
    event_id = sent_to(pushes, "elder-phone")[0].data["event_id"]

    assert (await api.get(f"{API}/reminders/{event_id}", headers=ctx["family"])).status_code == 200
    assert (await api.get(f"{API}/reminders/{event_id}", headers=ctx["stranger"])).json()["error"]["code"] == "NOT_BOUND"

    day = (await api.get(f"{ctx['base']}/reminders?date=2026-11-05", headers=ctx["family"])).json()
    assert [r["label"] for r in day] == ["早餐飯後", "晚餐飯後"]
    assert (await api.get(f"{ctx['base']}/reminders?date=2026-11-06", headers=ctx["family"])).json() == []


async def test_nudge(api: httpx.AsyncClient, ctx: dict, pushes: FakePusher) -> None:
    url = f"{ctx['base']}/nudge"
    assert (await api.post(url, headers=ctx["family"])).status_code == 204
    [message] = sent_to(pushes, "elder-phone")
    assert message.body == "陳小美提醒你吃藥喔"
    assert message.data["type"] == "medication_nudge"

    assert (await api.post(url, headers=ctx["elder"])).json()["error"]["code"] == "FAMILY_ONLY"
    assert (await api.post(url, headers=ctx["stranger"])).json()["error"]["code"] == "NOT_BOUND"


# ---------- 3-1 回診提醒 ----------


async def test_refill_reminder(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add(api, ctx, AMLODIPINE_10)  # 11/03 起 14 天，11/16 吃完 → 11/09 提醒

    freeze(monkeypatch, "2026-11-09 08:59")
    assert (await tick(api))["refill"] == 0
    freeze(monkeypatch, "2026-11-09 09:00")
    assert (await tick(api))["refill"] == 1
    text = "1 號的藥再 7 天就吃完囉，要記得回診或領慢箋"
    assert [m.body for m in sent_to(pushes, "elder-phone") if m.data["type"] == "refill_reminder"] == [text]
    assert [m.body for m in sent_to(pushes, "daughter-phone")] == [text]  # 家人端也收到

    freeze(monkeypatch, "2026-11-09 15:00")
    assert (await tick(api))["refill"] == 0  # 同一天不重複
    freeze(monkeypatch, "2026-11-10 09:00")
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
    api: httpx.AsyncClient, ctx: dict, demo_api: httpx.AsyncClient, pushes: FakePusher
) -> None:
    await add(api, ctx, AMLODIPINE_5)
    query = f"?elder_id={ctx['elder_id']}"

    resp = await demo_api.post(f"{API}/demo/trigger/reminder{query}", headers=ctx["family"])
    assert resp.status_code == 200, resp.text
    assert sent_to(pushes, "elder-phone")[0].body.startswith("陳阿嬤，吃藥時間到囉～")

    resp = await demo_api.post(f"{API}/demo/trigger/no-response{query}", headers=ctx["family"])
    assert resp.json()["status"] == "no_response"
    assert "沒有回應" in sent_to(pushes, "daughter-phone")[0].body

    resp = await demo_api.post(f"{API}/demo/trigger/refill{query}", headers=ctx["family"])
    assert resp.json() == {"numbers": [1]}

    # 一般模式沒有 demo API
    assert (await api.post(f"{API}/demo/trigger/refill{query}", headers=ctx["family"])).status_code == 404
