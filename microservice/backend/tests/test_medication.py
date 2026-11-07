"""藥單與藥品：新增藥單的三條路徑（掃 QR、拍照辨識、手動）、字母配發、今天四個時段。需要 PostgreSQL。"""

import asyncio
import datetime as dt
import gzip
import json
import uuid
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import clock
from app.integrations.fda.importer import import_licenses
from app.modules.medication.models import SlotKey
from app.modules.medication.service import MedicationService
from seed.load import load_licenses, sample_drug_codes
from tests.conftest import LoginFn

API = "/api/v1"
SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
SAMPLES = [s["payload"] for s in json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))]
RX_A, RX_B, RX_C = SAMPLES  # A：心臟內科 3 個藥；B：新陳代謝科 2 個藥；C：和 A1 同成分


def qr_reply(payload: dict | str | None) -> dict:
    """App 對 qr_code_scan 的回覆：data 是 QR 裡的字串。"""
    data = payload if payload is None or isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {"name": "qr_code_scan", "data": data}


def freeze(monkeypatch: pytest.MonkeyPatch, taipei: str) -> None:
    """把現在時間固定在台北時間 taipei（例如 '2026-11-05 10:00'）。"""
    at = dt.datetime.fromisoformat(taipei).replace(tzinfo=clock.TAIPEI).astimezone(dt.UTC)
    monkeypatch.setattr(clock, "now", lambda: at)


async def import_drugs(sessionmaker: async_sessionmaker[AsyncSession], keep: Callable[[dict], bool]) -> None:
    """從健保用藥品項匯入符合條件的品項（避免每個測試匯入 4.5 萬筆）。"""
    rows = json.loads(gzip.decompress((SEED / "nhi_drugs.json.gz").read_bytes()))["rows"]
    async with sessionmaker() as session:
        await import_licenses(session, [r for r in rows if keep(r)])
        await session.commit()


@pytest.fixture
async def ctx(api: httpx.AsyncClient, login: LoginFn, sessionmaker: async_sessionmaker[AsyncSession]) -> dict:
    async with sessionmaker() as session:
        await load_licenses(session, only=sample_drug_codes())
        await session.commit()
    elder_h, elder_id = await login("elder-1", "陳阿嬤", "elder")
    family_h, family_id = await login("family-1", "陳小美", "family")
    stranger_h, _ = await login("family-2", "路人", "family")
    base = f"{API}/elders/{elder_id}"
    return {"elder": elder_h, "family": family_h, "stranger": stranger_h, "elder_id": elder_id, "base": base}


async def preview(api: httpx.AsyncClient, ctx: dict, payload, who: str = "elder") -> httpx.Response:
    return await api.post(f"{ctx['base']}/prescriptions/qr-preview", json=qr_reply(payload), headers=ctx[who])


async def add(api: httpx.AsyncClient, ctx: dict, payload: dict, who: str = "elder") -> httpx.Response:
    """模擬完整流程：掃 QR 預覽 → 逐項核對 → 把 draft 原樣送回加入。"""
    resp = await preview(api, ctx, payload, who)
    if resp.status_code != 200:
        return resp
    return await api.post(f"{ctx['base']}/prescriptions", json=resp.json()["draft"], headers=ctx[who])


def manual_draft(**item) -> dict:
    """手動新增（E06m）：只有藥名、一次幾顆、時段、飯前飯後，院區科別可之後補填。"""
    return {
        "source": "manual",
        "visit_date": "2026-11-07",
        "days": 7,
        "items": [{"name": "Aspirin", "dose_qty": 1, "slots": ["morning"], "meal_timing": "after", **item}],
    }


async def bind_family(api: httpx.AsyncClient, ctx: dict) -> str:
    code = (await api.post(f"{API}/family/invites", headers=ctx["elder"])).json()["code"]
    resp = await api.post(f"{API}/family/bindings", json={"code": code, "relation_label": "媽媽"}, headers=ctx["family"])
    return resp.json()["id"]


# ---------- 路徑 1：掃藥袋 QR Code ----------


async def test_qr_preview_shows_confirm_screen(api: httpx.AsyncClient, ctx: dict) -> None:
    resp = await preview(api, ctx, RX_A)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # E06：配好的字母、每個藥的編號
    assert body["letter"] == "A"
    assert [i["code"] for i in body["items"]] == ["A1", "A2", "A3"]
    draft = body["draft"]
    assert (draft["source"], draft["hospital"], draft["department"], draft["doctor"], draft["days"]) == (
        "qr",
        "仁愛院區",
        "心臟內科",
        "王醫師",
        28,
    )
    first = draft["items"][0]
    assert (first["name"], first["license_no"], first["purpose"], first["quantity"]) == (
        "Amlodipine 5 毫克",
        "B021571100",
        "降血壓",
        28,
    )
    assert [(s["label"], s["time"]) for s in body["items"][2]["slots"]] == [("睡前", "22:00:00")]
    assert body["items"][0]["meal_timing_label"] == "飯後"
    # 加入完成頁的四個時段
    assert [(r["label"], r["codes"]) for r in body["schedule"]] == [
        ("早上", ["A1", "A2"]),
        ("中午", []),
        ("晚上", []),
        ("睡前", ["A3"]),
    ]
    assert body["uncertain"] == [] and body["warnings"] == []
    # 預覽不寫入
    assert (await api.get(f"{ctx['base']}/prescriptions", headers=ctx["elder"])).json() == []


@pytest.mark.parametrize(
    ("data", "code", "message"),
    [
        (None, "QR_EMPTY", None),  # 使用者取消掃描
        ("https://example.com", "QR_INVALID", None),  # 不是藥袋 QR
        ({**RX_A, "v": 3, "medicines": None}, "QR_INVALID", None),  # 不支援的格式
        ({"medicines": [{"name": "Aspirin"}]}, "QR_INVALID", "藥袋 QR Code 缺少：院區（hospital）"),
        ({"hospital": "仁愛院區", "medicines": []}, "QR_INVALID", "藥袋 QR Code 缺少：藥品清單（medicines）"),
        ({"hospital": "仁愛院區", "medicines": [{"amount": 1}]}, "QR_INVALID", "藥袋 QR Code 缺少：藥名（medicines[].name）"),
    ],
)
async def test_preview_rejects_bad_qr(api: httpx.AsyncClient, ctx: dict, data, code: str, message: str | None) -> None:
    resp = await preview(api, ctx, data)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == code
    if message:
        assert resp.json()["error"]["message"] == message


async def test_qr_defaults_and_formats(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """前端格式（docs/qrcode_format.md）：最少只要院區與藥名；民國日期、頻率代碼。"""
    freeze(monkeypatch, "2026-11-08 10:00")
    minimal = (await preview(api, ctx, {"hospital": "仁愛院區", "medicines": [{"name": "Aspirin 100 毫克"}]})).json()["draft"]
    item = minimal["items"][0]
    # 今天看診、早上吃 1 顆、飯後、28 顆
    assert (minimal["visit_date"], item["slots"], item["dose_qty"], item["meal_timing"], item["quantity"]) == (
        "2026-11-08",
        ["morning"],
        1,
        "after",
        28,
    )
    roc = {"hospital": "仁愛院區", "visitDate": "115.11.01", "days": 14,
           "medicines": [{"name": "Metformin", "frequency": "q12h", "amount": 0.5, "meal": "飯前"}]}  # fmt: skip
    draft = (await preview(api, ctx, roc)).json()["draft"]
    assert draft["visit_date"] == "2026-11-01"
    assert (draft["items"][0]["slots"], draft["items"][0]["meal_timing"], draft["items"][0]["quantity"]) == (
        ["morning", "evening"],
        "before",
        14,  # 14 天 × 每天 1 顆
    )
    # 舊版 v1 仍可掃
    v1 = {"v": 1, "t": "rx", "hosp": "仁愛院區", "dept": "家醫科", "dr": "林醫師", "date": "2026-11-01", "days": 28,
          "lic": "B025635100", "name": "Metformin", "use": "降血糖", "qty": 1, "freq": "BID", "meal": "bedtime"}  # fmt: skip
    assert (await preview(api, ctx, v1)).json()["draft"]["items"][0]["slots"] == ["bedtime"]


async def test_add_assigns_letters(api: httpx.AsyncClient, ctx: dict) -> None:
    first = await add(api, ctx, RX_A)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["prescription"]["letter"] == "A"
    assert [m["code"] for m in body["prescription"]["medications"]] == ["A1", "A2", "A3"]
    assert body["message"] == "請用筆在這個藥袋上寫一個大大的「A」。手機上的 A1、A2、A3，就是這個藥袋裡的藥。"
    assert [r["codes"] for r in body["schedule"]] == [["A1", "A2"], [], [], ["A3"]]

    second = (await add(api, ctx, RX_B)).json()
    assert second["prescription"]["letter"] == "B"
    assert [m["code"] for m in second["prescription"]["medications"]] == ["B1", "B2"]


async def test_same_ingredient_warning(api: httpx.AsyncClient, ctx: dict) -> None:
    await add(api, ctx, RX_A)
    await add(api, ctx, RX_B)

    # C1（壓可平錠）和 A1（脈優錠）不同牌子、同成分
    expected = [{"type": "same_ingredient", "code": "C1", "with_code": "A1", "message": "這兩包好像是同一種藥，請問藥師"}]
    body = (await preview(api, ctx, RX_C)).json()
    assert body["warnings"] == expected
    assert body["items"][0]["warnings"] == expected
    # 只標示，不阻擋
    added = await add(api, ctx, RX_C)
    assert added.status_code == 201
    assert added.json()["warnings"] == expected

    # 同一張藥單裡兩個同成分的藥也會標示
    draft = manual_draft(license_no="A037344100")
    draft["items"].append({**draft["items"][0], "name": "Aspirin 再一包"})
    warnings = (await api.post(f"{ctx['base']}/prescriptions/preview", json=draft, headers=ctx["elder"])).json()["warnings"]
    assert [(w["code"], w["with_code"]) for w in warnings] == [("D1", "A2"), ("D2", "A2"), ("D2", "D1")]


async def test_finished_prescription_releases_letter(
    api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze(monkeypatch, "2026-11-07 10:00")
    a = (await add(api, ctx, RX_A)).json()["prescription"]
    await add(api, ctx, RX_B)
    url = f"{ctx['base']}/prescriptions"

    finished = (await api.post(f"{url}/{a['id']}/finish", headers=ctx["elder"])).json()
    assert finished["status"] == "finished"
    assert (await api.post(f"{url}/{a['id']}/finish", headers=ctx["elder"])).status_code == 200  # 重複不會出錯
    assert [p["letter"] for p in (await api.get(url, headers=ctx["elder"])).json()] == ["B"]
    assert [p["letter"] for p in (await api.get(f"{url}?status=finished", headers=ctx["elder"])).json()] == ["A"]

    # A 空出來，新的藥單拿到 A
    assert (await add(api, ctx, RX_C)).json()["prescription"]["letter"] == "A"

    # 過了吃藥天數的藥單自動移到「已吃完」
    freeze(monkeypatch, "2026-12-31 10:00")
    assert (await api.get(url, headers=ctx["elder"])).json() == []
    assert len((await api.get(f"{url}?status=finished", headers=ctx["elder"])).json()) == 3


# ---------- 路徑 2：手動新增 ----------


async def test_manual_add_and_fill_in_later(api: httpx.AsyncClient, ctx: dict) -> None:
    draft = manual_draft(
        license_no="A037344100", strength="100 毫克", dose_qty=0.5, slots=["bedtime", "morning"], needs_review=True
    )
    shown = (await api.post(f"{ctx['base']}/prescriptions/preview", json=draft, headers=ctx["elder"])).json()
    # 時段可以複選，依時間排序
    assert [s["label"] for s in shown["items"][0]["slots"]] == ["早上", "睡前"]
    assert shown["letter"] == "A"

    created = (await api.post(f"{ctx['base']}/prescriptions", json=draft, headers=ctx["elder"])).json()["prescription"]
    assert (created["source"], created["department"], created["needs_review"]) == ("manual", None, True)
    assert created["medications"][0]["needs_review"] is True  # 劑量「看不清楚／不確定」→ 待核對

    # 科別可之後補填
    url = f"{ctx['base']}/prescriptions/{created['id']}"
    patched = (await api.patch(url, json={"department": "家醫科"}, headers=ctx["elder"])).json()
    assert patched["department"] == "家醫科"

    # 總顆數和天數至少要有一個
    no_days = {**draft, "days": None}
    resp = await api.post(f"{ctx['base']}/prescriptions", json=no_days, headers=ctx["elder"])
    assert resp.json()["error"]["code"] == "DAYS_REQUIRED"
    with_quantity = {**no_days, "items": [{**draft["items"][0], "quantity": 14}]}
    resp = await api.post(f"{ctx['base']}/prescriptions", json=with_quantity, headers=ctx["elder"])
    assert resp.status_code == 201
    assert resp.json()["prescription"]["days"] is None


async def test_search_drugs(api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await import_drugs(sessionmaker, lambda r: (r["product_en"] or "").startswith(("NORVASC", "LIPITOR", "NORCOL")))
    url = f"{API}/drugs/search"

    found = (await api.get(url, params={"q": "nor"}, headers=ctx["elder"])).json()
    # 同藥名只出現一次，再選劑量；北市聯醫常用藥排前面
    assert found[0]["name"] == "Norvasc"
    assert found[0]["name_zh"] == "脈優錠"
    assert [s["label"] for s in found[0]["strengths"]] == ["5 毫克", "10 毫克"]
    assert found[0]["common"] is True
    assert "Norcol" in [f["name"] for f in found[1:]]

    # 中文也可以；不分大小寫
    assert [f["name"] for f in (await api.get(url, params={"q": "脈優"}, headers=ctx["elder"])).json()] == ["Norvasc"]
    lipitor = (await api.get(url, params={"q": "LIPI"}, headers=ctx["elder"])).json()[0]
    assert [s["label"] for s in lipitor["strengths"]] == ["10 毫克", "20 毫克", "40 毫克"]
    # 打 2 個字以上才搜尋
    assert (await api.get(url, params={"q": "n"}, headers=ctx["elder"])).json() == []


# ---------- 路徑 3：拍照辨識（手機出欄位，後端比對打分） ----------


async def test_photo_preview_scores_fields(api: httpx.AsyncClient, ctx: dict) -> None:
    body = {
        "hospital": "臺北市立聯合醫院仁愛院區",
        "department": "心臟內科",
        "visit_date": "2026-11-05",
        "days": 28,
        "confidence": {"days": 0.5},
        "items": [
            {"name": "Norvsac", "strength": "5 毫克", "dose_qty": 1, "frequency": "QD", "meal_timing": "after", "confidence": {"name": 0.95}},
            {"name": "Asprin", "slots": ["morning"]},
            {"name": "XYZABC", "dose_qty": 1, "slots": ["noon"], "meal_timing": "before"},
        ],
    }  # fmt: skip
    resp = await api.post(f"{ctx['base']}/prescriptions/photo-preview", json=body, headers=ctx["elder"])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    draft = result["draft"]
    assert draft["source"] == "photo"
    # 辨識錯字也能對到健保藥品，帶入代號，同成分比對才有用
    assert draft["items"][0]["license_no"] == "B021571100"
    assert draft["items"][0]["slots"] == ["morning"]
    assert draft["items"][1]["license_no"] == "A037344100"  # Aspirin
    assert draft["items"][1]["strength"] == "100 毫克"  # 從健保資料補上
    assert draft["items"][2]["license_no"] is None  # 找不到就不帶入

    # 沒把握的欄位：紅框「電腦不確定這一項」
    assert {u["field"] for u in result["uncertain"]} == {
        "days",
        "items.1.dose_qty",
        "items.1.meal_timing",
        "items.2.name",
        "items.2.strength",
    }
    assert [(i["code"], i["uncertain"]) for i in result["items"]] == [("A1", False), ("A2", True), ("A3", True)]
    assert result["items"][1]["uncertain_fields"] == ["dose_qty", "meal_timing"]
    # 看不出來的欄位先填預設值，讓長輩修改
    assert (draft["items"][1]["dose_qty"], draft["items"][1]["meal_timing"]) == (1, "after")


# ---------- 我的藥單、今天四個時段 ----------


async def test_prescription_cards_and_today(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    freeze(monkeypatch, "2026-11-10 08:00")
    await add(api, ctx, RX_A)
    await add(api, ctx, RX_B)

    cards = (await api.get(f"{ctx['base']}/prescriptions", headers=ctx["elder"])).json()
    assert [(p["letter"], p["department"], p["visit_date"], p["days_left"]) for p in cards] == [
        ("A", "心臟內科", "2026-11-05", 23),
        ("B", "新陳代謝科", "2026-11-06", 24),
    ]
    a1 = cards[0]["medications"][0]
    # 還剩幾天 = 剩下顆數 ÷ 每天吃幾顆（28 顆、每天 1 顆，11/05 起）
    assert (a1["quantity"], a1["days_left"], a1["run_out_date"]) == (28, 23, "2026-12-02")
    # 念給我聽：藥名念健保中文品名
    assert a1["speech_text"] == "1 號藥，脈優錠５毫克，心臟內科開的，降血壓。一次 1 顆，飯後吃，早上 9 點。還剩 23 天。"
    assert a1["speech_text_en"].startswith("Medicine number 1, Amlodipine 5 mg, from Cardiology, for blood pressure.")

    today = (await api.get(f"{ctx['base']}/today", headers=ctx["elder"])).json()
    assert today["date"] == "2026-11-10"
    assert [(s["label"], s["time"], [i["code"] for i in s["items"]]) for s in today["slots"]] == [
        ("早上", "09:00:00", ["A1", "A2", "B1"]),
        ("中午", "12:00:00", ["B1", "B2"]),
        ("晚上", "18:00:00", ["B1"]),
        ("睡前", "22:00:00", ["A3"]),
    ]
    noon = today["slots"][1]
    assert [(g["letter"], g["department"], g["hospital"]) for g in noon["groups"]] == [
        ("B", "新陳代謝科", "中興院區")
    ]
    # UI E02：「中午十二點，要吃新陳代謝科一號一顆、二號一顆」（不念英文字母）
    assert noon["speech_text"] == "中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆"
    assert today["slots"][0]["speech_text"] == "早上 9 點，要吃心臟內科 1 號 1 顆、2 號 1 顆；新陳代謝科 1 號 1 顆"


async def test_detail_edit_and_stop(api: httpx.AsyncClient, ctx: dict) -> None:
    med = (await add(api, ctx, RX_A)).json()["prescription"]["medications"][0]
    url = f"{ctx['base']}/medications/{med['id']}"

    assert (await api.get(url, headers=ctx["elder"])).json()["code"] == "A1"
    edited = (await api.patch(url, json={"slots": ["noon", "morning"], "dose_qty": 0.5}, headers=ctx["elder"])).json()
    assert [s["slot_key"] for s in edited["slots"]] == ["morning", "noon"]
    assert "一次 半顆" in edited["speech_text"]

    stopped = await api.post(f"{url}/stop", json={"reason": "doctor_advised"}, headers=ctx["elder"])
    assert (stopped.json()["status"], stopped.json()["stop_reason"]) == ("stopped", "doctor_advised")
    assert (await api.post(f"{url}/stop", json={"reason": "finished"}, headers=ctx["elder"])).status_code == 200
    assert (await api.patch(url, json={"dose_qty": 1}, headers=ctx["elder"])).json()["error"]["code"] == "MEDICATION_STOPPED"
    # 停用的藥不再出現在今天的時段
    codes = [i["code"] for s in (await api.get(f"{ctx['base']}/today", headers=ctx["elder"])).json()["slots"] for i in s["items"]]
    assert "A1" not in codes

    assert (await api.get(f"{ctx['base']}/medications/{uuid.uuid4()}", headers=ctx["elder"])).status_code == 404


async def test_next_dose(api: httpx.AsyncClient, ctx: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"{ctx['base']}/next-dose"
    assert (await api.get(url, headers=ctx["elder"])).json() is None  # 還沒有藥

    await add(api, ctx, RX_B)  # 第一張藥單，配到 A：A1 早中晚、A2 中午

    freeze(monkeypatch, "2026-11-07 10:00")
    nxt = (await api.get(url, headers=ctx["elder"])).json()
    assert (nxt["label"], nxt["at"], nxt["is_today"]) == ("中午", "2026-11-07T12:00:00+08:00", True)
    assert [(i["code"], i["qty"]) for i in nxt["items"]] == [("A1", 1), ("A2", 1)]

    freeze(monkeypatch, "2026-11-07 19:00")
    nxt = (await api.get(url, headers=ctx["elder"])).json()
    assert (nxt["at"], nxt["is_today"]) == ("2026-11-08T09:00:00+08:00", False)

    # 藥都吃完了（超過天數）就沒有下一次
    freeze(monkeypatch, "2026-12-31 08:00")
    assert (await api.get(url, headers=ctx["elder"])).json() is None


# ---------- 權限：家人唯讀，僅綁定後第一次可設定 ----------


async def test_family_permissions(api: httpx.AsyncClient, ctx: dict) -> None:
    binding_id = await bind_family(api, ctx)

    # 初始設定期間，家人可以幫忙新增藥單
    assert (await add(api, ctx, RX_A, who="family")).status_code == 201

    await api.post(f"{API}/family/bindings/{binding_id}/complete-setup", headers=ctx["family"])

    # 之後只能看
    for path in ("prescriptions", "today", "next-dose"):
        assert (await api.get(f"{ctx['base']}/{path}", headers=ctx["family"])).status_code == 200
    resp = await preview(api, ctx, RX_B, who="family")
    assert (resp.status_code, resp.json()["error"]["code"]) == (403, "READ_ONLY")

    # 沒綁定的人什麼都不能看
    resp = await api.get(f"{ctx['base']}/prescriptions", headers=ctx["stranger"])
    assert resp.json()["error"]["code"] == "NOT_BOUND"


# ---------- 提供給其他模組 ----------


async def test_service_for_other_modules(
    api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await add(api, ctx, RX_A)  # 11/05 起 28 天
    await add(api, ctx, RX_B)  # 11/06 起 28 天
    elder_id = ctx["elder_id"]

    async with sessionmaker() as session:
        service = MedicationService(session)
        doses = await service.list_active_doses(elder_id, dt.date(2026, 11, 7))
        assert [(d.code, d.name) for d in doses][:2] == [("A1", "Amlodipine 5 毫克"), ("A2", "Aspirin 100 毫克")]
        assert await service.list_active_doses(elder_id, dt.date(2026, 12, 31)) == []

        noon = await service.slot_view(elder_id, SlotKey.NOON, dt.date(2026, 11, 7))
        assert noon is not None and [i.code for i in noon.items] == ["B1", "B2"]
        assert await service.slot_view(elder_id, SlotKey.NOON, dt.date(2026, 11, 5)) is None  # B 還沒開始吃

        # 最近看診的藥單（回診預約帶入科別）
        visit = await service.last_visit(elder_id)
        assert (visit.letter, visit.department, visit.doctor) == ("B", "新陳代謝科", "陳醫師")

        running_out = await service.running_out_on(dt.date(2026, 12, 2))  # A 吃完日
        assert [p.letter for p in running_out[elder_id]] == ["A"]
        assert await service.elders_scheduled_on(dt.date(2026, 11, 7)) == [elder_id]


async def test_concurrent_adds_get_distinct_letters(api: httpx.AsyncClient, ctx: dict) -> None:
    drafts = [(await preview(api, ctx, p)).json()["draft"] for p in SAMPLES]
    responses = await asyncio.gather(
        *(api.post(f"{ctx['base']}/prescriptions", json=d, headers=ctx["elder"]) for d in drafts)
    )
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    assert sorted(r.json()["prescription"]["letter"] for r in responses) == ["A", "B", "C"]
