"""回診預約：UI E10～E12、E16、F08。需要 PostgreSQL。

固定今天為 2026-11-05（星期四），可預約 11/06～11/19。
仁愛院區家醫科林醫師：星期一上午、星期二晚上、星期三上午、星期五上午有門診；
11/06 每個看診時間都額滿、11/09 停診（seed 的 Demo 設定）。
每個看診時間有預先填入的模擬預約數，所以看診號碼不一定從 1 號開始。
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
RX_A = json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))[0]["payload"]
# 仁愛院區家醫科林醫師開的藥單 → 預約時帶入科別與醫師
RX_FAMILY_MEDICINE = {**RX_A, "dept": "家醫科", "dr": "林醫師"}


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

    freeze(monkeypatch, "2026-11-05 10:00")
    qr = {"name": "qr_code_scan", "data": json.dumps(RX_FAMILY_MEDICINE, ensure_ascii=False)}
    draft = (await api.post(f"{ctx['base']}/prescriptions/qr-preview", json=qr, headers=elder_h)).json()["draft"]
    await api.post(f"{ctx['base']}/prescriptions", json=draft, headers=elder_h)
    return ctx


async def walk_to_doctor(api: httpx.AsyncClient, ctx: dict, hospital="仁愛院區", department="家醫科", doctor="林醫師") -> str:
    """選院區、科別、醫師，回傳醫師 id。"""
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    hospital_id = next(h["id"] for h in hospitals if h["name"].endswith(hospital))
    departments = (await api.get(f"{API}/hospitals/{hospital_id}/departments", headers=ctx["elder"])).json()
    department_id = next(d["id"] for d in departments if d["name"] == department)
    doctors = (await api.get(f"{API}/departments/{department_id}/doctors", headers=ctx["elder"])).json()
    return next(d["id"] for d in doctors if d["name"] == doctor)


async def session_id(api: httpx.AsyncClient, ctx: dict, day: str, **where) -> str:
    doctor_id = await walk_to_doctor(api, ctx, **where)
    days = (await api.get(f"{API}/doctors/{doctor_id}/sessions", headers=ctx["elder"])).json()
    return next(d["session_id"] for d in days if d["date"] == day)


async def open_slot(api: httpx.AsyncClient, ctx: dict, day: str, **where) -> dict:
    """這天門診第一個還有名額的看診時間。"""
    sid = await session_id(api, ctx, day, **where)
    slots = (await api.get(f"{API}/sessions/{sid}/slots", headers=ctx["elder"])).json()
    return next(s for s in slots if s["available"])


async def book(api: httpx.AsyncClient, ctx: dict, slot_id: str, who: str = "elder", base: str | None = None) -> httpx.Response:
    return await api.post(f"{base or ctx['base']}/appointments", json={"slot_id": slot_id}, headers=ctx[who])


# ---------- 選院區、科別、醫師、日期、時段 ----------


async def test_hospitals(api: httpx.AsyncClient, ctx: dict) -> None:
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    assert len(hospitals) == 9
    assert all(h["name"].startswith("臺北市立聯合醫院") for h in hospitals)
    renai = next(h for h in hospitals if h["name"].endswith("仁愛院區"))
    assert renai["address"] == "臺北市大安區仁愛路四段10號"
    # 「帶我去醫院」：App 的 launch_map 訊息
    assert renai["map"]["name"] == "launch_map"
    assert renai["map"]["data"].startswith("https://")


async def test_seven_campuses_and_departments_by_site(api: httpx.AsyncClient, ctx: dict) -> None:
    """北市聯醫 7 院區；和平婦幼、林森中醫昆明各有 2 個院址，分開列出（地址不同）。"""
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    names = [h["name"].removeprefix("臺北市立聯合醫院") for h in hospitals]
    assert len({n.split("（")[0] for n in names}) == 7
    assert {"和平婦幼院區（和平）", "和平婦幼院區（婦幼）", "林森中醫昆明院區（林森）", "林森中醫昆明院區（昆明）"} <= set(names)

    async def departments(site: str) -> list[str]:
        hospital_id = next(h["id"] for h in hospitals if h["name"].endswith(site))
        return [d["name"] for d in (await api.get(f"{API}/hospitals/{hospital_id}/departments", headers=ctx["elder"])).json()]

    assert "一般精神科" in await departments("松德院區")
    assert "家醫科" not in await departments("松德院區")
    assert set(await departments("（婦幼）")) == {"婦產科", "小兒科"}
    assert "中醫內科" in await departments("（林森）")


async def test_reseed_prunes_retired_hospitals_but_keeps_booked_sessions(
    api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    """院區改名後重新匯入：舊院區被移除；已被預約的門診保留，預約不受影響。"""
    async with sessionmaker() as session:
        for sql in (
            "INSERT INTO hospitals (id, name, address) VALUES ('00000000-0000-0000-0000-000000000001', '舊院區', 'x')",
            "INSERT INTO departments (id, hospital_id, name)"
            " VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', '家醫科')",
            "INSERT INTO doctors (id, department_id, name)"
            " VALUES ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', '舊醫師')",
        ):
            await session.execute(text(sql))
        await session.commit()
    done = (await book(api, ctx, (await open_slot(api, ctx, "2026-11-10"))["slot_id"])).json()

    async with sessionmaker() as session:
        await load_clinics(session, TODAY)
        await session.commit()
    names = [h["name"] for h in (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()]
    assert "舊院區" not in names and len(names) == 9
    assert (await api.get(f"{ctx['base']}/appointments", headers=ctx["elder"])).json()[0]["id"] == done["id"]


async def test_department_and_doctor_from_prescription(api: httpx.AsyncClient, ctx: dict) -> None:
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    renai = next(h["id"] for h in hospitals if h["name"].endswith("仁愛院區"))
    query = f"?elder_id={ctx['elder_id']}"

    # E10：「已從藥單 A 帶入科別」
    departments = (await api.get(f"{API}/hospitals/{renai}/departments{query}", headers=ctx["elder"])).json()
    assert (departments[0]["name"], departments[0]["last_visited"], departments[0]["from_letter"]) == ("家醫科", True, "A")
    assert sum(d["last_visited"] for d in departments) == 1

    doctors = (await api.get(f"{API}/departments/{departments[0]['id']}/doctors{query}", headers=ctx["elder"])).json()
    assert (doctors[0]["name"], doctors[0]["last_visited"]) == ("林醫師", True)
    # E10b：門診時間
    assert doctors[0]["schedule"] == "週一、週三、週五 上午；週二 晚上"
    assert (doctors[0]["available"], doctors[0]["note"]) == (True, None)

    other = next(d for d in departments if d["name"] == "心臟內科")
    doctors = (await api.get(f"{API}/departments/{other['id']}/doctors{query}", headers=ctx["elder"])).json()
    assert not any(d["last_visited"] for d in doctors)

    # 沒有綁定的人不能用別人的 elder_id
    resp = await api.get(f"{API}/hospitals/{renai}/departments{query}", headers=ctx["stranger"])
    assert resp.json()["error"]["code"] == "NOT_BOUND"


async def test_doctor_full_for_two_weeks(
    api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    doctor_id = await walk_to_doctor(api, ctx, department="家醫科", doctor="張醫師")
    async with sessionmaker() as session:
        await session.execute(
            text(
                "UPDATE clinic_slots SET booked_count = capacity WHERE session_id IN"
                " (SELECT id FROM clinic_sessions WHERE doctor_id = :id)"
            ),
            {"id": doctor_id},
        )
        await session.commit()
    hospitals = (await api.get(f"{API}/hospitals", headers=ctx["elder"])).json()
    renai = next(h["id"] for h in hospitals if h["name"].endswith("仁愛院區"))
    departments = (await api.get(f"{API}/hospitals/{renai}/departments", headers=ctx["elder"])).json()
    department_id = next(d["id"] for d in departments if d["name"] == "家醫科")
    doctors = (await api.get(f"{API}/departments/{department_id}/doctors", headers=ctx["elder"])).json()
    zhang = next(d for d in doctors if d["name"] == "張醫師")
    assert (zhang["available"], zhang["note"]) == (False, "已額滿")  # 灰色不可選


async def test_clinic_days_and_slots(api: httpx.AsyncClient, ctx: dict) -> None:
    doctor_id = await walk_to_doctor(api, ctx)
    days = (await api.get(f"{API}/doctors/{doctor_id}/sessions", headers=ctx["elder"])).json()

    # E10f：只列出這位醫師未來 2 週的門診
    assert [d["date"] for d in days] == [
        "2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11",
        "2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18",
    ]  # fmt: skip
    assert (days[4]["label"], days[4]["period_label"]) == ("11/13（五）", "上午門診")
    assert days[2]["period_label"] == "晚上門診"
    # 額滿、停診：灰色不可選
    assert (days[0]["available"], days[0]["note"]) == (False, "已額滿")
    assert (days[1]["available"], days[1]["note"], days[1]["status"]) == (False, "停診", "suspended")
    assert (days[2]["available"], days[2]["note"]) == (True, None)

    # E10g：每個看診時間的剩餘名額
    slots = (await api.get(f"{API}/sessions/{days[4]['session_id']}/slots", headers=ctx["elder"])).json()
    assert [s["label"] for s in slots] == ["上午 08:30", "上午 09:00", "上午 09:30", "上午 10:00", "上午 10:30", "上午 11:00"]
    for s in slots:
        assert s["note"] == ("已額滿" if s["remaining"] == 0 else f"還有 {s['remaining']} 個名額")
        assert s["available"] is (s["remaining"] > 0)
    full_day = (await api.get(f"{API}/sessions/{days[0]['session_id']}/slots", headers=ctx["elder"])).json()
    assert {s["note"] for s in full_day} == {"已額滿"}
    suspended = (await api.get(f"{API}/sessions/{days[1]['session_id']}/slots", headers=ctx["elder"])).json()
    assert {(s["available"], s["note"]) for s in suspended} == {(False, "停診")}


# ---------- 確認預約、預約成功 ----------


async def test_book(api: httpx.AsyncClient, ctx: dict) -> None:
    slot = await open_slot(api, ctx, "2026-11-13")
    resp = await book(api, ctx, slot["slot_id"])
    assert resp.status_code == 201, resp.text
    done = resp.json()
    # E12：看診號碼、日期、時段、院區、科別、醫師
    assert done["hospital"]["name"] == "臺北市立聯合醫院仁愛院區"
    assert (done["department"], done["doctor"]) == ("家醫科", "林醫師")
    assert (done["date_label"], done["time_label"]) == ("11/13（五）", slot["label"])
    assert done["visit_no"] >= 1
    assert done["message"] == "回診前一天，您和家屬都會收到提醒。"
    assert done["hospital"]["map"]["name"] == "launch_map"

    # 名額少 1
    sid = await session_id(api, ctx, "2026-11-13")
    after = next(s for s in (await api.get(f"{API}/sessions/{sid}/slots", headers=ctx["elder"])).json() if s["slot_id"] == slot["slot_id"])
    assert after["remaining"] == slot["remaining"] - 1

    # 同一個門診（即使不同時間）不能重複預約
    other = await open_slot(api, ctx, "2026-11-13")
    assert (await book(api, ctx, other["slot_id"])).json()["error"]["code"] == "ALREADY_BOOKED"


async def test_cannot_book_full_or_suspended(
    api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    full_day = await session_id(api, ctx, "2026-11-06")
    suspended_day = await session_id(api, ctx, "2026-11-09")
    full = (await api.get(f"{API}/sessions/{full_day}/slots", headers=ctx["elder"])).json()[0]
    suspended = (await api.get(f"{API}/sessions/{suspended_day}/slots", headers=ctx["elder"])).json()[0]
    assert (await book(api, ctx, full["slot_id"])).json()["error"]["code"] == "SLOT_FULL"
    assert (await book(api, ctx, suspended["slot_id"])).json()["error"]["code"] == "SESSION_SUSPENDED"
    missing = "00000000-0000-0000-0000-000000000000"
    assert (await book(api, ctx, missing)).json()["error"]["code"] == "SLOT_NOT_FOUND"


async def test_cannot_book_outside_window(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    slot = await open_slot(api, ctx, "2026-11-10")
    freeze(monkeypatch, "2026-11-10 08:00")  # 當天不能預約（明天起）
    assert (await book(api, ctx, slot["slot_id"])).json()["error"]["code"] == "SESSION_OUT_OF_RANGE"


async def test_visit_numbers_not_reused(api: httpx.AsyncClient, ctx: dict, login: LoginFn) -> None:
    slot_id = (await open_slot(api, ctx, "2026-11-10"))["slot_id"]
    others = []
    for i in (2, 3):
        headers, elder_id = await login(f"elder-{i}", f"長輩{i}", "elder")
        ctx[f"elder{i}"] = headers
        others.append(f"{API}/elders/{elder_id}")

    first = (await book(api, ctx, slot_id)).json()
    second = (await book(api, ctx, slot_id, who="elder2", base=others[0])).json()
    assert second["visit_no"] == first["visit_no"] + 1
    await api.post(f"{ctx['base']}/appointments/{first['id']}/cancel", headers=ctx["elder"])
    # 取消後名額釋出，但號碼不重複發
    third = (await book(api, ctx, slot_id, who="elder3", base=others[1])).json()
    assert third["visit_no"] == first["visit_no"] + 2


async def test_last_seat_race(
    api: httpx.AsyncClient, ctx: dict, login: LoginFn, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    slot_id = (await open_slot(api, ctx, "2026-11-10"))["slot_id"]
    async with sessionmaker() as session:
        await session.execute(text("UPDATE clinic_slots SET capacity = booked_count + 1 WHERE id = :id"), {"id": slot_id})
        await session.commit()
    headers, elder_id = await login("elder-2", "長輩2", "elder")
    ctx["elder2"] = headers
    results = await asyncio.gather(
        book(api, ctx, slot_id), book(api, ctx, slot_id, who="elder2", base=f"{API}/elders/{elder_id}")
    )
    assert sorted(r.status_code for r in results) == [201, 409]


# ---------- 我的預約 ----------


async def test_my_appointments_and_cancel(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    later = (await book(api, ctx, (await open_slot(api, ctx, "2026-11-17"))["slot_id"])).json()
    sooner = (await book(api, ctx, (await open_slot(api, ctx, "2026-11-11"))["slot_id"])).json()
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
    slot = await open_slot(api, ctx, "2026-11-10")
    assert (await book(api, ctx, slot["slot_id"], who="family")).status_code == 201  # 初始設定期間可以幫忙預約

    await api.post(f"{API}/family/bindings/{ctx['binding_id']}/complete-setup", headers=ctx["family"])
    assert (await api.get(f"{ctx['base']}/appointments", headers=ctx["family"])).status_code == 200
    other = (await open_slot(api, ctx, "2026-11-11"))["slot_id"]
    assert (await book(api, ctx, other, who="family")).json()["error"]["code"] == "READ_ONLY"
    assert (await book(api, ctx, other, who="stranger")).json()["error"]["code"] == "NOT_BOUND"


# ---------- 回診前一天 18:00 自動提醒（UI E16、F08） ----------


async def tick(api: httpx.AsyncClient) -> dict:
    resp = await api.post(f"{API}/internal/tick", headers={"X-Internal-Secret": get_settings().internal_secret})
    return resp.json()


def appointment_pushes(pushes: FakePusher, token: str) -> list[tuple[str, str]]:
    return [(m.title, m.body) for tokens, m in pushes.sent if token in tokens and m.data["type"] == "appointment_reminder"]


async def test_appointment_reminder_day_before(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    slot = await open_slot(api, ctx, "2026-11-13")
    await book(api, ctx, slot["slot_id"])
    at = slot["time"][:5]

    freeze(monkeypatch, "2026-11-12 17:59")
    assert (await tick(api))["appointment"] == 0
    freeze(monkeypatch, "2026-11-12 18:00")
    assert (await tick(api))["appointment"] == 1
    assert (await tick(api))["appointment"] == 0  # 不重複
    freeze(monkeypatch, "2026-11-13 08:00")
    assert (await tick(api))["appointment"] == 0  # 當天不再提醒

    assert appointment_pushes(pushes, "elder-phone") == [(f"明天 {at} 要回診", "仁愛院區家醫科林醫師，記得帶健保卡")]
    assert appointment_pushes(pushes, "daughter-phone") == [
        (f"陳阿嬤 明天 {at} 要回診", "仁愛院區家醫科林醫師，記得提醒或陪伴他")
    ]
    message = next(m for _, m in pushes.sent if m.data["type"] == "appointment_reminder")
    assert json.loads(message.data["map"])["name"] == "launch_map"


async def test_cancelled_appointment_not_reminded(
    api: httpx.AsyncClient, ctx: dict, pushes: FakePusher, monkeypatch: pytest.MonkeyPatch
) -> None:
    done = (await book(api, ctx, (await open_slot(api, ctx, "2026-11-13"))["slot_id"])).json()
    await api.post(f"{ctx['base']}/appointments/{done['id']}/cancel", headers=ctx["elder"])
    freeze(monkeypatch, "2026-11-12 18:00")
    assert (await tick(api))["appointment"] == 0
