"""family 模組：邀請碼、綁定、權限檢查。需要 PostgreSQL。"""

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import Forbidden
from app.modules.family import rules
from app.modules.family.service import Access, FamilyService
from tests.conftest import LoginFn

API = "/api/v1"


@pytest.fixture
async def people(login: LoginFn) -> dict:
    elder_h, elder_id = await login("elder-1", "陳阿嬤", "elder")
    family_h, family_id = await login("family-1", "陳小美", "family")
    stranger_h, stranger_id = await login("family-2", "路人", "family")
    return {
        "elder": (elder_h, elder_id),
        "family": (family_h, family_id),
        "stranger": (stranger_h, stranger_id),
    }


async def _invite(api: httpx.AsyncClient, headers: dict) -> dict:
    resp = await api.post(f"{API}/family/invites", headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _bind(api: httpx.AsyncClient, headers: dict, **body) -> httpx.Response:
    return await api.post(f"{API}/family/bindings", json={"relation_label": "媽媽", **body}, headers=headers)


# ---------- 邀請碼 ----------


async def test_create_invite(api: httpx.AsyncClient, people: dict) -> None:
    invite = await _invite(api, people["elder"][0])
    assert len(invite["code"]) == 6 and invite["code"].isdigit()
    assert invite["qr_url"].endswith(f"/invite/{invite['code']}")


async def test_only_elder_can_invite(api: httpx.AsyncClient, people: dict) -> None:
    resp = await api.post(f"{API}/family/invites", headers=people["family"][0])
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ELDER_ONLY"


async def test_role_required(api: httpx.AsyncClient, login: LoginFn) -> None:
    headers, _ = await login("no-role", "還沒選", None)
    resp = await api.post(f"{API}/family/invites", headers=headers)
    assert resp.json()["error"]["code"] == "ROLE_REQUIRED"


async def test_bind_with_code(api: httpx.AsyncClient, people: dict) -> None:
    invite = await _invite(api, people["elder"][0])
    resp = await _bind(api, people["family"][0], code=invite["code"])
    assert resp.status_code == 201, resp.text
    binding = resp.json()
    assert binding["elder_name"] == "陳阿嬤"
    assert binding["family_name"] == "陳小美"
    assert binding["relation_label"] == "媽媽"
    assert binding["can_setup"] is True

    for who in ("elder", "family"):
        listed = (await api.get(f"{API}/family/bindings", headers=people[who][0])).json()
        assert [b["id"] for b in listed] == [binding["id"]]
    assert (await api.get(f"{API}/family/bindings", headers=people["stranger"][0])).json() == []


async def test_bind_with_app_qr_reply(api: httpx.AsyncClient, people: dict) -> None:
    invite = await _invite(api, people["elder"][0])
    # 家人用 App 掃邀請 QR：App 回覆 { name: 'qr_code_scan', data: <QR 內容> }
    qr = {"name": "qr_code_scan", "data": invite["qr_url"]}
    resp = await _bind(api, people["family"][0], qr=qr)
    assert resp.status_code == 201, resp.text


async def test_bind_requires_qr_or_code(api: httpx.AsyncClient, people: dict) -> None:
    resp = await _bind(api, people["family"][0])
    assert resp.status_code == 400
    # 使用者取消掃描（data 為 null）也算沒提供
    resp = await _bind(api, people["family"][0], qr={"name": "qr_code_scan", "data": None})
    assert resp.status_code == 400


async def test_invite_used_once(api: httpx.AsyncClient, people: dict) -> None:
    invite = await _invite(api, people["elder"][0])
    assert (await _bind(api, people["family"][0], code=invite["code"])).status_code == 201
    resp = await _bind(api, people["stranger"][0], code=invite["code"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVITE_USED"


async def test_invite_expired(
    api: httpx.AsyncClient, people: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    invite = await _invite(api, people["elder"][0])
    async with sessionmaker() as session:
        await session.execute(text("UPDATE family_invites SET expires_at = now() - interval '1 second'"))
        await session.commit()
    resp = await _bind(api, people["family"][0], code=invite["code"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVITE_EXPIRED"


async def test_new_invite_replaces_old(api: httpx.AsyncClient, people: dict) -> None:
    old = await _invite(api, people["elder"][0])
    new = await _invite(api, people["elder"][0])
    if old["code"] == new["code"]:  # 極少數情況下抽到同一組
        pytest.skip("隨機到相同邀請碼")
    assert (await _bind(api, people["family"][0], code=old["code"])).json()["error"]["code"] == "INVITE_EXPIRED"
    assert (await _bind(api, people["family"][0], code=new["code"])).status_code == 201


async def test_invite_not_found(api: httpx.AsyncClient, people: dict) -> None:
    resp = await _bind(api, people["family"][0], code="000000")
    assert resp.status_code == 404


async def test_only_family_can_bind(api: httpx.AsyncClient, people: dict, login: LoginFn) -> None:
    other_elder_h, _ = await login("elder-2", "王阿公", "elder")
    invite = await _invite(api, people["elder"][0])
    resp = await _bind(api, other_elder_h, code=invite["code"])
    assert resp.json()["error"]["code"] == "FAMILY_ONLY"


async def test_already_bound_keeps_invite_unused(api: httpx.AsyncClient, people: dict) -> None:
    first = await _invite(api, people["elder"][0])
    assert (await _bind(api, people["family"][0], code=first["code"])).status_code == 201
    second = await _invite(api, people["elder"][0])
    resp = await _bind(api, people["family"][0], code=second["code"])
    assert resp.json()["error"]["code"] == "ALREADY_BOUND"
    # 交易沒有 commit，邀請碼還能給別人用
    assert (await _bind(api, people["stranger"][0], code=second["code"])).status_code == 201


# ---------- 綁定的管理 ----------


async def _bound(api: httpx.AsyncClient, people: dict) -> dict:
    invite = await _invite(api, people["elder"][0])
    return (await _bind(api, people["family"][0], code=invite["code"])).json()


async def test_family_updates_binding(api: httpx.AsyncClient, people: dict) -> None:
    binding = await _bound(api, people)
    url = f"{API}/family/bindings/{binding['id']}"
    resp = await api.patch(url, json={"notify_on_ack": False, "relation_label": "阿母"}, headers=people["family"][0])
    assert resp.json()["notify_on_ack"] is False
    assert resp.json()["relation_label"] == "阿母"
    assert (await api.patch(url, json={"notify_on_ack": True}, headers=people["elder"][0])).status_code == 403


async def test_complete_setup(api: httpx.AsyncClient, people: dict) -> None:
    binding = await _bound(api, people)
    url = f"{API}/family/bindings/{binding['id']}/complete-setup"
    assert (await api.post(url, headers=people["elder"][0])).status_code == 403
    assert (await api.post(url, headers=people["family"][0])).json()["can_setup"] is False
    # 重複呼叫不會出錯
    assert (await api.post(url, headers=people["family"][0])).status_code == 200


async def test_revoke(api: httpx.AsyncClient, people: dict) -> None:
    binding = await _bound(api, people)
    url = f"{API}/family/bindings/{binding['id']}"
    assert (await api.delete(url, headers=people["family"][0])).status_code == 403
    assert (await api.delete(url, headers=people["elder"][0])).status_code == 204
    assert (await api.get(f"{API}/family/bindings", headers=people["family"][0])).json() == []
    assert (await api.delete(url, headers=people["elder"][0])).status_code == 404


# ---------- 權限檢查 ----------


async def test_ensure_access(
    api: httpx.AsyncClient, people: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    binding = await _bound(api, people)
    elder_id, family_id, stranger_id = (people[k][1] for k in ("elder", "family", "stranger"))

    async def check(user_id, access: Access) -> str | None:
        async with sessionmaker() as session:
            try:
                await FamilyService(session).ensure_access(user_id, elder_id, access)
                return None
            except Forbidden as exc:
                return exc.code

    assert await check(elder_id, Access.WRITE) is None
    assert await check(family_id, Access.READ) is None
    assert await check(family_id, Access.WRITE) is None  # 初始設定期間可以寫
    assert await check(stranger_id, Access.READ) == "NOT_BOUND"

    await api.post(f"{API}/family/bindings/{binding['id']}/complete-setup", headers=people["family"][0])
    assert await check(family_id, Access.READ) is None
    assert await check(family_id, Access.WRITE) == "READ_ONLY"

    await api.delete(f"{API}/family/bindings/{binding['id']}", headers=people["elder"][0])
    assert await check(family_id, Access.READ) == "NOT_BOUND"

    # 家人不能把自己當成長輩
    async with sessionmaker() as session:
        with pytest.raises(Forbidden):
            await FamilyService(session).ensure_access(family_id, family_id, Access.READ)


async def test_list_family_ids(
    api: httpx.AsyncClient, people: dict, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    binding = await _bound(api, people)
    await api.patch(
        f"{API}/family/bindings/{binding['id']}", json={"notify_on_ack": False}, headers=people["family"][0]
    )
    async with sessionmaker() as session:
        service = FamilyService(session)
        assert await service.list_family_ids(people["elder"][1]) == [people["family"][1]]
        assert await service.list_family_ids(people["elder"][1], ack_subscribers_only=True) == []


def test_code_from_input() -> None:
    assert rules.code_from_input(" 123 456 ") == "123456"
    assert rules.code_from_input("https://x.web.app/invite/654321") == "654321"
    assert rules.code_from_input("12345") is None
    assert rules.code_from_input("https://x.web.app/c/TPE-AAAA-BBBB") is None
