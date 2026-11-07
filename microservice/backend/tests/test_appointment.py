"""回診預約：功能規格 3-2、3-3，交付規格第 8 點。需要 PostgreSQL。

固定今天為 2026-11-05（星期四），可預約 11/06～11/19。
仁愛院區家醫科林醫師：星期一上午、星期二晚上、星期三上午、星期五上午有門診；
11/06 額滿、11/09 停診（seed 的 Demo 設定）。
"""

import asyncio
import datetime as dt
import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import clock
from app.core.config import get_settings
from seed.load import load_clinics
from tests.conftest import FakePusher, LoginFn

API = "/api/v1"
TODAY = dt.date(2026, 11, 5)
SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
RX_1 = json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))[0]["payload"]  # 仁愛院區 家醫科 林醫師


def freeze(monkeypatch: pytest.MonkeyPatch, taipei: str) -> None:
    at = dt.datetime.fromisoformat(taipei).replace(tzinfo=clock.TAIPEI).astimezone(dt.UTC)
    monkeypatch.setattr(clock, "now", lambda: at)


@pytest.fixture
async def ctx(
    api: httpx.AsyncClient,
    login: LoginFn,
    pushes: FakePusher,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    async with sessionmaker() as session:
        await load_clinics(session, TODAY)
        await session.commit()
    elder_h, elder_id = await login("elder-1", "陳阿嬤", "elder")
    family_h, _ = await login("family-1", "陳小美", "family")
    stranger_h, _ = await login("family-2", "路人", "family")
    ctx = {"elder": elder_h, "family": family_h, "stranger": stranger_h, "elder_id": elder_id}
    ctx["base"] = f"{API}/elders/{elder_id}"

    code = (await api.post(f"{API}/family/invites", headers=elder_h)).json()["code"]
    binding = await api.post(f"{API}/family/bindings", json={"code": code, "relation_label": "媽媽"}, headers=family_h)
    ctx["binding_id"] = binding.json()["id"]
    for who, token in (("elder", "elder-phone"), ("family", "daughter-phone")):
        await api.post(f"{API}/devices", json={"name": "push_token", "data": {"token": token, "platform": "ios"}}, headers=ctx[who])

    # 掃過仁愛院區家醫科林醫師開的藥 → 上次看的科別、醫師
    qr = {"name": "qr_code_scan", "data": json.dumps(RX_1, ensure_ascii=False)}
    draft = (await api.post(f"{ctx['base']}/medications/qr-preview", json=qr, headers=elder_h)).json()["draft"]
    await api.post(f"{ctx['base']}/medications", json=draft, headers=elder_h)

    freeze(monkeypatch, "2026-11-05 10:00")
    return ctx


async def walk_to_doctor(api: httpx.AsyncClient, ctx: dict, hospital="仁愛院區", department="家醫科", doctor="林醫師") -> str:
    """步驟 1～3，回傳醫師 id。"""
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    hospital_id = next(h["id"] for h in hospitals if h["name"].endswith(hospital))
    departments = (await api.get(f"{API}/hospitals/{hospital_id}/departments", headers=ctx["elder"])).json()
    department_id = next(d["id"] for d in departments if d["name"] == department)
    doctors = (await api.get(f"{API}/departments/{department_id}/doctors", headers=ctx["elder"])).json()
    return next(d["id"] for d in doctors if d["name"] == doctor)


async def session_id(api: httpx.AsyncClient, ctx: dict, day: str, period: str, **where) -> str:
    doctor_id = await walk_to_doctor(api, ctx, **where)
    days = (await api.get(f"{API}/doctors/{doctor_id}/sessions", headers=ctx["elder"])).json()
    return next(s["session_id"] for d in days if d["date"] == day for s in d["sessions"] if s["period"] == period)


async def book(api: httpx.AsyncClient, ctx: dict, sid: str, who: str = "elder", base: str | None = None) -> httpx.Response:
    return await api.post(f"{base or ctx['base']}/appointments", json={"session_id": sid}, headers=ctx[who])


# ---------- 步驟 1～5 ----------


async def test_hospitals(api: httpx.AsyncClient, ctx: dict) -> None:
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    assert len(hospitals) == 9
    assert all(h["name"].startswith("臺北市立聯合醫院") for h in hospitals)
    renai = next(h for h in hospitals if h["name"].endswith("仁愛院區"))
    assert renai["address"] == "臺北市大安區仁愛路四段10號"
    # 「帶我去醫院」：App 的 launch_map 訊息
    assert renai["map"]["name"] == "launch_map"
    assert renai["map"]["data"].startswith("https://")


async def test_last_visited_department_and_doctor_first(api: httpx.AsyncClient, ctx: dict) -> None:
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    renai = next(h["id"] for h in hospitals if h["name"].endswith("仁愛院區"))
    query = f"?elder_id={ctx['elder_id']}"

    departments = (await api.get(f"{API}/hospitals/{renai}/departments{query}", headers=ctx["elder"])).json()
    assert (departments[0]["name"], departments[0]["last_visited"]) == ("家醫科", True)
    assert sum(d["last_visited"] for d in departments) == 1

    doctors = (await api.get(f"{API}/departments/{departments[0]['id']}/doctors{query}", headers=ctx["elder"])).json()
    assert (doctors[0]["name"], doctors[0]["last_visited"]) == ("林醫師", True)

    other = next(d for d in departments if d["name"] == "心臟內科")
    doctors = (await api.get(f"{API}/departments/{other['id']}/doctors{query}", headers=ctx["elder"])).json()
    assert not any(d["last_visited"] for d in doctors)

    # 沒有綁定的人不能用別人的 elder_id
    resp = await api.get(f"{API}/hospitals/{renai}/departments{query}", headers=ctx["stranger"])
    assert resp.json()["error"]["code"] == "NOT_BOUND"


async def test_clinic_days(api: httpx.AsyncClient, ctx: dict) -> None:
    doctor_id = await walk_to_doctor(api, ctx)
    days = (await api.get(f"{API}/doctors/{doctor_id}/sessions", headers=ctx["elder"])).json()

    # 只列出這位醫師未來 2 週有門診的日子
    assert [d["date"] for d in days] == [
        "2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11",
        "2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18",
    ]
    assert days[3]["label"] == "11/11（星期三）"
    assert [(s["label"], s["period"]) for s in days[2]["sessions"]] == [("晚上", "evening")]
    # 額滿、停診：灰色不可選
    assert (days[0]["available"], days[0]["sessions"][0]["status"]) == (False, "open")
    assert (days[1]["available"], days[1]["sessions"][0]["status"]) == (False, "suspended")
    assert days[2]["available"] is True


# ---------- 步驟 6：確認預約、完成頁 ----------


async def test_book(api: httpx.AsyncClient, ctx: dict) -> None:
    sid = await session_id(api, ctx, "2026-11-10", "evening")
    resp = await book(api, ctx, sid)
    assert resp.status_code == 201, resp.text
    done = resp.json()
    assert done["hospital"]["name"] == "臺北市立聯合醫院仁愛院區"
    assert (done["department"], done["doctor"]) == ("家醫科", "林醫師")
    assert (done["date_label"], done["period_label"], done["visit_no"]) == ("11/10（星期二）", "晚上", 1)
    assert done["hospital"]["map"]["name"] == "launch_map"
    assert done["reminder_enabled"] is False

    assert (await book(api, ctx, sid)).json()["error"]["code"] == "ALREADY_BOOKED"


async def test_cannot_book_full_or_suspended(api: httpx.AsyncClient, ctx: dict) -> None:
    full = await session_id(api, ctx, "2026-11-06", "morning")
    suspended = await session_id(api, ctx, "2026-11-09", "morning")
    assert (await book(api, ctx, full)).json()["error"]["code"] == "SESSION_FULL"
    assert (await book(api, ctx, suspended)).json()["error"]["code"] == "SESSION_SUSPENDED"


async def test_cannot_book_outside_window(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    sid = await session_id(api, ctx, "2026-11-10", "evening")
    freeze(monkeypatch, "2026-11-10 08:00")  # 當天不能預約（明天起）
    assert (await book(api, ctx, sid)).json()["error"]["code"] == "SESSION_OUT_OF_RANGE"


async def test_visit_numbers_not_reused(api: httpx.AsyncClient, ctx: dict, login: LoginFn) -> None:
    sid = await session_id(api, ctx, "2026-11-10", "evening")
    others = []
    for i in (2, 3):
        headers, elder_id = await login(f"elder-{i}", f"長輩{i}", "elder")
        ctx[f"elder{i}"] = headers
        others.append(f"{API}/elders/{elder_id}")

    first = (await book(api, ctx, sid)).json()
    assert (await book(api, ctx, sid, who="elder2", base=others[0])).json()["visit_no"] == 2
    await api.post(f"{ctx['base']}/appointments/{first['id']}/cancel", headers=ctx["elder"])
    # 1 號取消後名額釋出，但新預約拿 3 號，不重複發 1 號
    assert (await book(api, ctx, sid, who="elder3", base=others[1])).json()["visit_no"] == 3


async def test_last_seat_race(
    api: httpx.AsyncClient, ctx: dict, login: LoginFn, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    sid = await session_id(api, ctx, "2026-11-10", "evening")
    async with sessionmaker() as session:
        await session.execute(text("UPDATE clinic_sessions SET capacity = 1 WHERE id = :id"), {"id": sid})
        await session.commit()
    headers, elder_id = await login("elder-2", "長輩2", "elder")
    ctx["elder2"] = headers
    results = await asyncio.gather(
        book(api, ctx, sid), book(api, ctx, sid, who="elder2", base=f"{API}/elders/{elder_id}")
    )
    assert sorted(r.status_code for r in results) == [201, 409]


# ---------- 3-3 我的預約 ----------


async def test_my_appointments_and_cancel(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    later = (await book(api, ctx, await session_id(api, ctx, "2026-11-17", "evening"))).json()
    sooner = (await book(api, ctx, await session_id(api, ctx, "2026-11-11", "morning"))).json()
    mine = (await api.get(f"{ctx['base']}/appointments", headers=ctx["elder"])).json()
    assert [a["id"] for a in mine] == [sooner["id"], later["id"]]

    url = f"{ctx['base']}/appointments/{later['id']}/cancel"
    assert (await api.post(url, headers=ctx["elder"])).json()["status"] == "cancelled"
    assert (await api.post(url, headers=ctx["elder"])).status_code == 200  # 重複取消不會出錯
    assert [a["id"] for a in (await api.get(f"{ctx['base']}/appointments", headers=ctx["elder"])).json()] == [sooner["id"]]

    freeze(monkeypatch, "2026-11-12 09:00")
    resp = await api.post(f"{ctx['base']}/appointments/{sooner['id']}/cancel", headers=ctx["elder"])
    assert resp.json()["error"]["code"] == "APPOINTMENT_PAST"


async def test_family_permissions(api: httpx.AsyncClient, ctx: dict) -> None:
    sid = await session_id(api, ctx, "2026-11-10", "evening")
    assert (await book(api, ctx, sid, who="family")).status_code == 201  # 初始設定期間可以幫忙預約

    await api.post(f"{API}/family/bindings/{ctx['binding_id']}/complete-setup", headers=ctx["family"])
    assert (await api.get(f"{ctx['base']}/appointments", headers=ctx["family"])).status_code == 200
    other = await session_id(api, ctx, "2026-11-11", "morning")
    assert (await book(api, ctx, other, who="family")).json()["error"]["code"] == "READ_ONLY"
    assert (await book(api, ctx, other, who="stranger")).json()["error"]["code"] == "NOT_BOUND"


# ---------- 完成頁「加入提醒」：前一天 18:00、當天 08:00 ----------


async def tick(api: httpx.AsyncClient) -> dict:
    resp = await api.post(f"{API}/internal/tick", headers={"X-Internal-Secret": get_settings().internal_secret})
    return resp.json()


def appointment_pushes(pushes: FakePusher, token: str) -> list[str]:
    return [m.body for tokens, m in pushes.sent if token in tokens and m.data["type"] == "appointment_reminder"]


async def test_appointment_reminders(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    done = (await book(api, ctx, await session_id(api, ctx, "2026-11-10", "evening"))).json()
    url = f"{ctx['base']}/appointments/{done['id']}/reminder"
    assert (await api.put(url, json={"enabled": True}, headers=ctx["elder"])).json()["reminder_enabled"] is True

    freeze(monkeypatch, "2026-11-09 17:59")
    assert (await tick(api))["appointment"] == 0
    freeze(monkeypatch, "2026-11-09 18:00")
    assert (await tick(api))["appointment"] == 1
    assert (await tick(api))["appointment"] == 0  # 不重複

    freeze(monkeypatch, "2026-11-10 08:00")
    assert (await tick(api))["appointment"] == 1

    expected = [
        "明天晚上 仁愛院區 家醫科 林醫師 回診，看診號碼 1 號",
        "今天晚上 仁愛院區 家醫科 林醫師 回診，看診號碼 1 號",
    ]
    assert appointment_pushes(pushes, "elder-phone") == expected
    assert appointment_pushes(pushes, "daughter-phone") == expected  # 家人也收到
    message = next(m for _, m in pushes.sent if m.data["type"] == "appointment_reminder")
    assert json.loads(message.data["map"])["name"] == "launch_map"


async def test_no_reminder_unless_enabled(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    done = (await book(api, ctx, await session_id(api, ctx, "2026-11-10", "evening"))).json()
    freeze(monkeypatch, "2026-11-09 18:00")
    assert (await tick(api))["appointment"] == 0

    await api.post(f"{ctx['base']}/appointments/{done['id']}/cancel", headers=ctx["elder"])
    resp = await api.put(f"{ctx['base']}/appointments/{done['id']}/reminder", json={"enabled": True}, headers=ctx["elder"])
    assert resp.json()["error"]["code"] == "APPOINTMENT_CANCELLED"
