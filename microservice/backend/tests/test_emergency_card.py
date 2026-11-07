"""救命卡與救護人員：功能規格「二、救命卡」2-1～2-5。需要 PostgreSQL。"""

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.responder.rate_limit import lookup_limiter
from seed.load import load_licenses, load_responders
from tests.conftest import FakePusher, LoginFn

API = "/api/v1"
SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
RX_1 = json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))[0]["payload"]

CARD = {
    "title": "陳阿嬤",
    "birth_year": 1948,
    "gender": "female",
    "chronic_conditions": ["高血壓", "糖尿病", "高血壓"],
    "allergies": [{"type": "drug", "name": "盤尼西林"}, {"type": "food", "name": "海鮮"}],
}
CONTACTS = [
    {"name": "陳小美", "relation": "女兒", "phone": "0912-345-678"},
    {"name": "陳大同", "relation": "兒子", "phone": "0923 456 789"},
]


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    lookup_limiter.reset()


@pytest.fixture
async def ctx(api: httpx.AsyncClient, login: LoginFn, sessionmaker: async_sessionmaker[AsyncSession]) -> dict:
    async with sessionmaker() as session:
        await load_licenses(session)
        await load_responders(session)
        await session.commit()
    elder_h, elder_id = await login("elder-1", "陳阿嬤", "elder")
    family_h, _ = await login("family-1", "陳小美", "family")
    stranger_h, _ = await login("family-2", "路人", "family")
    base = f"{API}/elders/{elder_id}"
    return {"elder": elder_h, "family": family_h, "stranger": stranger_h, "base": base}


async def bind_family(api: httpx.AsyncClient, ctx: dict, label: str = "媽媽") -> str:
    code = (await api.post(f"{API}/family/invites", headers=ctx["elder"])).json()["code"]
    resp = await api.post(f"{API}/family/bindings", json={"code": code, "relation_label": label}, headers=ctx["family"])
    return resp.json()["id"]


async def setup_card(api: httpx.AsyncClient, ctx: dict, who: str = "elder") -> dict:
    """勾選同意 → 填救命卡 → 設定緊急聯絡人。"""
    assert (await api.post(f"{ctx['base']}/consents", json={}, headers=ctx[who])).status_code == 201
    resp = await api.put(f"{ctx['base']}/emergency-card", json=CARD, headers=ctx[who])
    assert resp.status_code == 200, resp.text
    resp = await api.put(f"{ctx['base']}/emergency-card/contacts", json={"contacts": CONTACTS}, headers=ctx[who])
    assert resp.status_code == 200, resp.text
    return resp.json()


async def responder_login(api: httpx.AsyncClient, account: str = "EMT-001") -> dict:
    resp = await api.post(f"{API}/responder/login", json={"account": account, "password": f"demo-{account.lower()}"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def lookup(api: httpx.AsyncClient, headers: dict, **body) -> httpx.Response:
    return await api.post(f"{API}/responder/cards/lookup", json=body, headers=headers)


def qr_reply(data: str | None) -> dict:
    return {"name": "qr_code_scan", "data": data}


LOCATION = {"name": "location", "data": {"latitude": 25.0478, "longitude": 121.5171, "timestamp": 1762500000000}}


# ---------- 2-1、2-2 我的救命卡、編輯 ----------


async def test_consent_required(api: httpx.AsyncClient, ctx: dict) -> None:
    resp = await api.put(f"{ctx['base']}/emergency-card", json=CARD, headers=ctx["elder"])
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CONSENT_REQUIRED"
    assert (await api.get(f"{ctx['base']}/emergency-card", headers=ctx["elder"])).json()["error"]["code"] == "CARD_NOT_CREATED"


async def test_my_card(api: httpx.AsyncClient, ctx: dict) -> None:
    preview = await api.post(f"{ctx['base']}/medications/qr-preview", json=qr_reply(json.dumps(RX_1)), headers=ctx["elder"])
    await api.post(f"{ctx['base']}/medications", json=preview.json()["draft"], headers=ctx["elder"])

    card = await setup_card(api, ctx)
    assert (card["title"], card["birth_year"], card["gender"]) == ("陳阿嬤", 1948, "female")
    assert card["hospital"] == "臺北市立聯合醫院"
    assert card["chronic_conditions"] == ["高血壓", "糖尿病"]  # 去除重複
    assert [a["name"] for a in card["allergies"]] == ["盤尼西林", "海鮮"]
    # 正在吃的藥從藥區自動帶入
    assert [(m["number"], m["name"]) for m in card["current_medications"]] == [(1, "Amlodipine 5mg")]
    # 緊急聯絡人：一鍵撥號訊息照 App 的 phone_call 格式
    assert card["contacts"][0]["call"] == {"name": "phone_call", "data": "0912345678"}
    assert card["has_consent"] is True
    assert card["access_logs"] == []
    # 卡號與 QR 內容
    assert card["code"]["code"].startswith("TPE-")
    assert card["code"]["qr_url"].endswith(f"/c/{card['code']['code']}")


async def test_contacts_limit(api: httpx.AsyncClient, ctx: dict) -> None:
    await setup_card(api, ctx)
    three = {"contacts": CONTACTS + [{"name": "鄰居", "relation": "鄰居", "phone": "0934567890"}]}
    resp = await api.put(f"{ctx['base']}/emergency-card/contacts", json=three, headers=ctx["elder"])
    assert resp.status_code == 400
    bad = {"contacts": [{"name": "x", "relation": "x", "phone": "請打給我"}]}
    assert (await api.put(f"{ctx['base']}/emergency-card/contacts", json=bad, headers=ctx["elder"])).status_code == 400


async def test_common_items(api: httpx.AsyncClient) -> None:
    items = (await api.get(f"{API}/emergency-card/common-items")).json()
    assert "高血壓" in items["chronic_conditions"]
    assert {"type": "drug", "name": "盤尼西林"} in items["allergies"]


async def test_family_permissions(api: httpx.AsyncClient, ctx: dict) -> None:
    binding_id = await bind_family(api, ctx)
    # 初始設定期間，家人可以幫忙勾選同意、填寫
    await setup_card(api, ctx, who="family")

    await api.post(f"{API}/family/bindings/{binding_id}/complete-setup", headers=ctx["family"])
    assert (await api.get(f"{ctx['base']}/emergency-card", headers=ctx["family"])).status_code == 200
    resp = await api.put(f"{ctx['base']}/emergency-card", json=CARD, headers=ctx["family"])
    assert resp.json()["error"]["code"] == "READ_ONLY"
    # 卡片遺失時，家人仍可重新產生卡號（功能規格 2-3）
    assert (await api.post(f"{ctx['base']}/emergency-card/regenerate-code", headers=ctx["family"])).status_code == 200

    assert (await api.get(f"{ctx['base']}/emergency-card", headers=ctx["stranger"])).json()["error"]["code"] == "NOT_BOUND"


# ---------- 2-3 卡號 ----------


async def test_regenerate_code(api: httpx.AsyncClient, ctx: dict) -> None:
    old = (await setup_card(api, ctx))["code"]["code"]
    new = (await api.post(f"{ctx['base']}/emergency-card/regenerate-code", headers=ctx["elder"])).json()["code"]
    assert new != old

    emt = await responder_login(api)
    assert (await lookup(api, emt, code=old)).json()["error"]["code"] == "CARD_NOT_FOUND"  # 舊卡號立即失效
    assert (await lookup(api, emt, code=new)).status_code == 200


async def test_revoke_consent(api: httpx.AsyncClient, ctx: dict) -> None:
    await bind_family(api, ctx)
    code = (await setup_card(api, ctx))["code"]["code"]
    url = f"{ctx['base']}/consents/health_data"

    assert (await api.delete(url, headers=ctx["family"])).json()["error"]["code"] == "ELDER_ONLY"
    assert (await api.delete(url, headers=ctx["elder"])).status_code == 204

    card = (await api.get(f"{ctx['base']}/emergency-card", headers=ctx["elder"])).json()
    assert (card["has_consent"], card["chronic_conditions"], card["allergies"], card["code"]) == (False, [], [], None)
    assert len(card["contacts"]) == 2
    emt = await responder_login(api)
    assert (await lookup(api, emt, code=code)).status_code == 404

    # 重新同意並儲存後補發新卡號
    new = await setup_card(api, ctx)
    assert new["code"]["code"] != code


# ---------- 2-4 救護人員 ----------


async def test_responder_login(api: httpx.AsyncClient, ctx: dict) -> None:
    ok = await api.post(f"{API}/responder/login", json={"account": "emt-001", "password": "demo-emt-001"})
    assert ok.status_code == 200
    assert (ok.json()["name"], ok.json()["unit"]) == ("王大明", "中山分隊")

    wrong = await api.post(f"{API}/responder/login", json={"account": "EMT-001", "password": "x"})
    unknown = await api.post(f"{API}/responder/login", json={"account": "EMT-999", "password": "x"})
    assert wrong.json() == unknown.json()  # 不透露帳號是否存在
    assert wrong.status_code == 401

    # 已離職：顯示「無權限」
    resigned = await api.post(f"{API}/responder/login", json={"account": "EMT-003", "password": "demo-emt-003"})
    assert resigned.status_code == 403
    assert resigned.json()["error"] == {"code": "RESPONDER_NOT_AUTHORIZED", "message": "無權限"}


async def test_tokens_are_not_interchangeable(api: httpx.AsyncClient, ctx: dict) -> None:
    emt = await responder_login(api)
    assert (await api.get(f"{API}/me", headers=emt)).status_code == 401
    assert (await lookup(api, ctx["elder"], code="TPE-2222-2222")).status_code == 401


async def test_resigned_after_login(
    api: httpx.AsyncClient, ctx: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    code = (await setup_card(api, ctx))["code"]["code"]
    emt = await responder_login(api)
    async with sessionmaker() as session:
        await session.execute(text("UPDATE responders SET employment_status = 'resigned' WHERE account = 'EMT-001'"))
        await session.commit()
    resp = await lookup(api, emt, code=code)
    assert resp.json()["error"]["code"] == "RESPONDER_NOT_AUTHORIZED"


async def test_lookup_input_formats(api: httpx.AsyncClient, ctx: dict) -> None:
    code = (await setup_card(api, ctx))["code"]["code"]
    emt = await responder_login(api)
    # QR 刮花時手動輸入：忽略大小寫、空白、連字號
    assert (await lookup(api, emt, code=code.lower().replace("-", " "))).status_code == 200
    assert (await lookup(api, emt, code="hello")).json()["error"]["code"] == "CARD_CODE_INVALID"
    assert (await lookup(api, emt, qr=qr_reply("https://example.com"))).json()["error"]["code"] == "CARD_CODE_INVALID"
    assert (await lookup(api, emt, code="TPE-2222-2222")).status_code == 404
    # qr 與 code 擇一
    assert (await lookup(api, emt)).status_code == 400
    assert (await lookup(api, emt, qr=qr_reply(None))).status_code == 400


async def test_rate_limit(api: httpx.AsyncClient, ctx: dict) -> None:
    emt = await responder_login(api)
    for _ in range(10):
        assert (await lookup(api, emt, code="TPE-2222-2222")).status_code == 404
    resp = await lookup(api, emt, code="TPE-2222-2222")
    assert resp.status_code == 429


# ---------- 2-5 Demo 流程 ----------


async def test_demo_flow(api: httpx.AsyncClient, ctx: dict, pushes: FakePusher) -> None:
    """路人掃 QR 只看到「請撥 119」（前端公開頁，不呼叫後端）
    → 救護人員登入後掃同一張卡看到完整資料 → 女兒手機收到通知。"""
    await bind_family(api, ctx, label="媽媽")
    await api.post(f"{API}/devices", json={"name": "push_token", "data": {"token": "daughter-phone", "platform": "ios"}}, headers=ctx["family"])
    card = await setup_card(api, ctx)

    # 救護人員在台北通內掃 QR：前端把 App 的 qr_code_scan、location 回覆原封不動送來
    emt = await responder_login(api)
    resp = await lookup(api, emt, qr=qr_reply(card["code"]["qr_url"]), location=LOCATION)
    assert resp.status_code == 200, resp.text
    shown = resp.json()

    # 顯示順序：過敏 → 正在吃的藥 → 慢性病 → 緊急聯絡人
    keys = list(shown)
    assert keys.index("allergies") < keys.index("current_medications") < keys.index("chronic_conditions") < keys.index("contacts")
    assert shown["contacts"][0]["call"] == {"name": "phone_call", "data": "0912345678"}
    assert shown["disclaimer"] == "本資料由本人或家屬提供，僅供參考，請以醫療專業判斷為準"
    assert shown["close_at"]  # 30 分鐘後自動關閉

    # 留紀錄：哪位救護人員、什麼時間、什麼地點
    logs = (await api.get(f"{ctx['base']}/emergency-card", headers=ctx["elder"])).json()["access_logs"]
    assert len(logs) == 1
    assert (logs[0]["responder_name"], logs[0]["responder_unit"], logs[0]["method"]) == ("王大明", "中山分隊", "qr")
    assert (float(logs[0]["latitude"]), float(logs[0]["longitude"])) == (25.0478, 121.5171)

    # 女兒收到通知，附一鍵撥號給救護人員的分隊
    assert len(pushes.sent) == 1
    tokens, message = pushes.sent[0]
    assert tokens == ["daughter-phone"]
    assert message.body.startswith("臺北市消防局中山分隊王大明於 ")
    assert message.body.endswith(" 查看了媽媽的救命卡")
    assert message.data["type"] == "card_accessed"
    assert json.loads(message.data["call"]) == {"name": "phone_call", "data": "0200000001"}
