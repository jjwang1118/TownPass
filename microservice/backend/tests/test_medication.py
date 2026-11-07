"""medication 模組：功能規格「一、藥」1-1～1-4。需要 PostgreSQL。"""

import datetime as dt
import json
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import clock
from app.integrations.fda.importer import import_licenses
from app.modules.medication.models import SlotKey
from app.modules.medication.service import MedicationService
from tests.conftest import LoginFn

API = "/api/v1"
SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
SAMPLES = [s["payload"] for s in json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))]
AMLODIPINE_5, METFORMIN, AMLODIPINE_10 = SAMPLES


def qr_reply(payload: dict | str | None) -> dict:
    """App 對 qr_code_scan 的回覆：data 是 QR 裡的字串。"""
    data = payload if payload is None or isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {"name": "qr_code_scan", "data": data}


def freeze(monkeypatch: pytest.MonkeyPatch, taipei: str) -> None:
    """把現在時間固定在台北時間 taipei（例如 '2026-11-05 10:00'）。"""
    at = dt.datetime.fromisoformat(taipei).replace(tzinfo=clock.TAIPEI).astimezone(dt.UTC)
    monkeypatch.setattr(clock, "now", lambda: at)


@pytest.fixture
async def ctx(api: httpx.AsyncClient, login: LoginFn, sessionmaker: async_sessionmaker[AsyncSession]) -> dict:
    async with sessionmaker() as session:
        await import_licenses(session, json.loads((SEED / "drug_licenses.json").read_text(encoding="utf-8")))
        await session.commit()
    elder_h, elder_id = await login("elder-1", "陳阿嬤", "elder")
    family_h, family_id = await login("family-1", "陳小美", "family")
    stranger_h, _ = await login("family-2", "路人", "family")
    base = f"{API}/elders/{elder_id}"
    return {"elder": elder_h, "family": family_h, "stranger": stranger_h, "elder_id": elder_id, "base": base}


async def preview(api: httpx.AsyncClient, ctx: dict, payload, who: str = "elder") -> httpx.Response:
    return await api.post(f"{ctx['base']}/medications/qr-preview", json=qr_reply(payload), headers=ctx[who])


async def add(api: httpx.AsyncClient, ctx: dict, payload: dict, who: str = "elder") -> httpx.Response:
    """模擬完整流程：掃 QR 預覽 → 長輩核對 → 把 draft 原樣送回加入。"""
    resp = await preview(api, ctx, payload, who)
    if resp.status_code != 200:
        return resp
    return await api.post(f"{ctx['base']}/medications", json=resp.json()["draft"], headers=ctx[who])


async def bind_family(api: httpx.AsyncClient, ctx: dict) -> str:
    code = (await api.post(f"{API}/family/invites", headers=ctx["elder"])).json()["code"]
    resp = await api.post(f"{API}/family/bindings", json={"code": code, "relation_label": "媽媽"}, headers=ctx["family"])
    return resp.json()["id"]


# ---------- 1-2 新增藥品：掃藥袋 QR ----------


async def test_preview_shows_confirm_screen(api: httpx.AsyncClient, ctx: dict) -> None:
    resp = await preview(api, ctx, METFORMIN)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 確認畫面核對藥名、劑量、頻率
    assert body["draft"]["name"] == "Metformin 500mg"
    assert body["draft"]["dose_qty"] == 1
    assert body["frequency_label"] == "一天兩次"
    assert body["meal_timing_label"] == "飯後"
    assert [(s["label"], s["time"]) for s in body["slots"]] == [("早餐飯後", "08:00:00"), ("晚餐飯後", "18:00:00")]
    assert body["warnings"] == []
    # 預覽不寫入
    assert (await api.get(f"{ctx['base']}/medications", headers=ctx["elder"])).json() == []


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (None, "QR_EMPTY"),  # 使用者取消掃描
        ("https://example.com", "QR_INVALID"),  # 不是藥袋 QR
        ({**METFORMIN, "v": 2}, "QR_INVALID"),  # 不支援的版本
        ({k: v for k, v in METFORMIN.items() if k != "qty"}, "QR_INVALID"),  # 缺欄位
    ],
)
async def test_preview_rejects_bad_qr(api: httpx.AsyncClient, ctx: dict, data, code: str) -> None:
    resp = await preview(api, ctx, data)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == code


async def test_add_assigns_numbers(api: httpx.AsyncClient, ctx: dict) -> None:
    first = await add(api, ctx, AMLODIPINE_5)
    assert first.status_code == 201, first.text
    assert first.json()["medication"]["number"] == 1
    assert first.json()["message"] == "請在藥袋上寫上大大的 1"

    second = (await add(api, ctx, METFORMIN)).json()
    assert second["medication"]["number"] == 2
    assert second["message"] == "請在藥袋上寫上大大的 2"


async def test_same_ingredient_warning(api: httpx.AsyncClient, ctx: dict) -> None:
    await add(api, ctx, AMLODIPINE_5)
    await add(api, ctx, METFORMIN)

    expected = [{"type": "same_ingredient", "with_number": 1, "message": "這兩包好像是同一種藥，請問藥師"}]
    assert (await preview(api, ctx, AMLODIPINE_10)).json()["warnings"] == expected
    # 只標示，不阻擋
    added = await add(api, ctx, AMLODIPINE_10)
    assert added.status_code == 201
    assert added.json()["warnings"] == expected
    assert added.json()["medication"]["number"] == 3


async def test_same_license_warns_even_without_fda_data(api: httpx.AsyncClient, ctx: dict) -> None:
    unknown = {**METFORMIN, "lic": "NOT-IN-FDA-DATA"}
    await add(api, ctx, unknown)
    warnings = (await preview(api, ctx, unknown)).json()["warnings"]
    assert [w["with_number"] for w in warnings] == [1]


# ---------- 1-1 我的藥 ----------


async def test_medication_card(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    freeze(monkeypatch, "2026-11-10 09:00")
    await add(api, ctx, AMLODIPINE_5)
    await add(api, ctx, AMLODIPINE_10)
    cards = (await api.get(f"{ctx['base']}/medications", headers=ctx["elder"])).json()

    assert [c["number"] for c in cards] == [1, 2]
    card = cards[0]
    # 大編號、藥名、一次幾顆、時段與時間、還剩幾天
    assert (card["number"], card["name"], card["dose_qty"]) == (1, "Amlodipine 5mg", 1)
    assert [(s["label"], s["time"]) for s in card["slots"]] == [("早餐飯後", "08:00:00")]
    assert card["run_out_date"] == "2026-11-28"
    assert card["days_left"] == 19  # 11/10～11/28

    # 念給我聽：藥名念食藥署許可證的中文品名（範例資料的中文品名本身含英文）
    assert card["speech_text"] == (
        "1 號藥，Amlodipine 5 毫克錠（範例），家醫科開的，降血壓。一次 1 顆，飯後吃，早上 8 點。還剩 19 天。"
    )
    assert "Amlodipine 10 毫克錠（範例）" in cards[1]["speech_text"]
    # 英文稿（給外籍看護）：藥名用藥袋上的英文，科別、用途翻成英文
    assert card["speech_text_en"] == (
        "Medicine number 1, Amlodipine 5mg, from Family Medicine, for blood pressure. "
        "Take 1 tablet after meals, at 8 AM. 19 days left."
    )
    assert "半顆" in cards[1]["speech_text"]


# ---------- 1-3 藥品詳細頁：編輯、停用 ----------


async def test_detail_and_edit(api: httpx.AsyncClient, ctx: dict) -> None:
    med = (await add(api, ctx, METFORMIN)).json()["medication"]
    url = f"{ctx['base']}/medications/{med['id']}"

    detail = (await api.get(url, headers=ctx["elder"])).json()
    for field in ("number", "name", "purpose", "dose_qty", "frequency", "meal_timing", "start_date", "days", "hospital", "department"):
        assert detail[field] == med[field]

    edited = (await api.patch(url, json={"frequency": "TID", "dose_qty": 0.5}, headers=ctx["elder"])).json()
    assert [s["slot_key"] for s in edited["slots"]] == ["breakfast_after", "lunch_after", "dinner_after"]
    assert "一次 半顆" in edited["speech_text"]

    assert (await api.get(f"{ctx['base']}/medications/{uuid.uuid4()}", headers=ctx["elder"])).status_code == 404


async def test_stop_releases_number(api: httpx.AsyncClient, ctx: dict) -> None:
    first = (await add(api, ctx, AMLODIPINE_5)).json()["medication"]
    await add(api, ctx, METFORMIN)
    url = f"{ctx['base']}/medications/{first['id']}"

    stopped = await api.post(f"{url}/stop", json={"reason": "doctor_advised"}, headers=ctx["elder"])
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["stop_reason"] == "doctor_advised"
    # 重複停用不會出錯
    assert (await api.post(f"{url}/stop", json={"reason": "finished"}, headers=ctx["elder"])).status_code == 200
    # 停用的藥不能再修改
    assert (await api.patch(url, json={"days": 7}, headers=ctx["elder"])).json()["error"]["code"] == "MEDICATION_STOPPED"

    active = (await api.get(f"{ctx['base']}/medications", headers=ctx["elder"])).json()
    assert [m["number"] for m in active] == [2]
    every = (await api.get(f"{ctx['base']}/medications?include_stopped=true", headers=ctx["elder"])).json()
    assert [(m["number"], m["status"]) for m in every] == [(2, "active"), (1, "stopped")]

    # 1 號空出來，新藥拿到 1 號
    assert (await add(api, ctx, AMLODIPINE_10)).json()["medication"]["number"] == 1


# ---------- 1-4 提醒時間設定 ----------


async def test_time_slots(api: httpx.AsyncClient, ctx: dict) -> None:
    url = f"{ctx['base']}/time-slots"
    slots = (await api.get(url, headers=ctx["elder"])).json()
    assert [(s["slot_key"], s["time"]) for s in slots] == [
        ("breakfast_before", "07:30:00"),
        ("breakfast_after", "08:00:00"),
        ("lunch_before", "11:30:00"),
        ("lunch_after", "12:00:00"),
        ("dinner_before", "17:30:00"),
        ("dinner_after", "18:00:00"),
        ("bedtime", "21:00:00"),
    ]

    resp = await api.put(url, json={"slots": [{"slot_key": "breakfast_after", "time": "09:00"}]}, headers=ctx["elder"])
    assert dict((s["slot_key"], s["time"]) for s in resp.json())["breakfast_after"] == "09:00:00"

    # 藥卡跟著新的時間
    await add(api, ctx, AMLODIPINE_5)
    card = (await api.get(f"{ctx['base']}/medications", headers=ctx["elder"])).json()[0]
    assert card["slots"][0]["time"] == "09:00:00"
    assert "早上 9 點" in card["speech_text"]

    dup = [{"slot_key": "bedtime", "time": "21:00"}, {"slot_key": "bedtime", "time": "22:00"}]
    assert (await api.put(url, json={"slots": dup}, headers=ctx["elder"])).json()["error"]["code"] == "DUPLICATE_SLOT"


# ---------- 首頁狀態列：下一次吃藥 ----------


async def test_next_dose(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"{ctx['base']}/next-dose"
    assert (await api.get(url, headers=ctx["elder"])).json() is None  # 還沒有藥

    await add(api, ctx, AMLODIPINE_5)  # 每天 08:00
    await add(api, ctx, METFORMIN)  # 每天 08:00、18:00

    freeze(monkeypatch, "2026-11-05 10:00")
    nxt = (await api.get(url, headers=ctx["elder"])).json()
    assert (nxt["label"], nxt["at"], nxt["is_today"]) == ("晚餐飯後", "2026-11-05T18:00:00+08:00", True)
    assert [i["number"] for i in nxt["items"]] == [2]

    freeze(monkeypatch, "2026-11-05 19:00")
    nxt = (await api.get(url, headers=ctx["elder"])).json()
    assert (nxt["at"], nxt["is_today"]) == ("2026-11-06T08:00:00+08:00", False)
    assert [(i["number"], i["qty"]) for i in nxt["items"]] == [(1, 1), (2, 1)]

    # 藥都吃完了（超過天數）就沒有下一次
    freeze(monkeypatch, "2026-12-31 08:00")
    assert (await api.get(url, headers=ctx["elder"])).json() is None


# ---------- 權限：家人唯讀，僅綁定後第一次可設定 ----------


async def test_family_permissions(api: httpx.AsyncClient, ctx: dict) -> None:
    binding_id = await bind_family(api, ctx)

    # 初始設定期間，家人可以幫忙掃藥袋、調時段
    assert (await add(api, ctx, AMLODIPINE_5, who="family")).status_code == 201
    slot = {"slots": [{"slot_key": "bedtime", "time": "22:00"}]}
    assert (await api.put(f"{ctx['base']}/time-slots", json=slot, headers=ctx["family"])).status_code == 200

    await api.post(f"{API}/family/bindings/{binding_id}/complete-setup", headers=ctx["family"])

    # 之後只能看
    assert (await api.get(f"{ctx['base']}/medications", headers=ctx["family"])).status_code == 200
    assert (await api.get(f"{ctx['base']}/next-dose", headers=ctx["family"])).status_code == 200
    for resp in (
        await preview(api, ctx, METFORMIN, who="family"),
        await api.put(f"{ctx['base']}/time-slots", json=slot, headers=ctx["family"]),
    ):
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "READ_ONLY"

    # 沒綁定的人什麼都不能看
    resp = await api.get(f"{ctx['base']}/medications", headers=ctx["stranger"])
    assert resp.json()["error"]["code"] == "NOT_BOUND"


# ---------- 提供給其他模組 ----------


async def test_service_for_other_modules(
    api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await add(api, ctx, AMLODIPINE_5)  # 11/01 起 28 天
    await add(api, ctx, METFORMIN)
    elder_id = ctx["elder_id"]

    async with sessionmaker() as session:
        service = MedicationService(session)
        doses = await service.list_active_doses(elder_id, dt.date(2026, 11, 5))
        assert [(d.number, d.name) for d in doses] == [(1, "Amlodipine 5mg"), (2, "Metformin 500mg")]
        assert await service.list_active_doses(elder_id, dt.date(2026, 12, 31)) == []

        dinner = await service.doses_for_slot(elder_id, SlotKey.DINNER_AFTER, dt.date(2026, 11, 5))
        assert [d.number for d in dinner] == [2]

        # 同一天開的藥，取最後加入的
        visit = await service.last_visit(elder_id)
        assert (visit.hospital, visit.department, visit.doctor) == ("臺北市立聯合醫院仁愛院區", "新陳代謝科", "陳醫師")


async def test_concurrent_adds_get_distinct_numbers(api: httpx.AsyncClient, ctx: dict) -> None:
    import asyncio

    drafts = [(await preview(api, ctx, p)).json()["draft"] for p in SAMPLES]
    responses = await asyncio.gather(
        *(api.post(f"{ctx['base']}/medications", json=d, headers=ctx["elder"]) for d in drafts)
    )
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    assert sorted(r.json()["medication"]["number"] for r in responses) == [1, 2, 3]
