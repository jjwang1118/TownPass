"""確認後端 schema 和城市通 App 實際傳出的格式一致。"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.integrations.townpass.messages import (
    BuiltinMessageName,
    LaunchMapMessage,
    LocationReply,
    NotifyMessage,
    PhoneCallMessage,
    PushTokenReply,
    QRCodeScanReply,
    UserinfoReply,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_ACCOUNT = REPO_ROOT / "assets" / "mock_data" / "account.json"
LISTENER = REPO_ROOT / "lib" / "util" / "web_message_handler" / "tp_web_message_listener.dart"
HANDLERS = REPO_ROOT / "lib" / "util" / "web_message_handler" / "tp_web_message_handler.dart"


def _reply(name: str, data: object) -> dict:
    """模擬網頁端 JSON.parse(event.data) 的結果（TPWebStringMessageReply 格式）。"""
    return json.loads(json.dumps({"name": name, "data": data}, ensure_ascii=False))


def test_builtin_names_match_app_source() -> None:
    import re

    names = set(re.findall(r"String get name => '([^']+)';", HANDLERS.read_text(encoding="utf-8")))
    assert names == {m.value for m in BuiltinMessageName}
    for cls in re.findall(r"(\w+)\(\),", LISTENER.read_text(encoding="utf-8")):
        assert cls in HANDLERS.read_text(encoding="utf-8")


def test_userinfo_reply_parses_app_mock_account() -> None:
    account = json.loads(MOCK_ACCOUNT.read_text(encoding="utf-8"))["data"]
    reply = UserinfoReply.model_validate(_reply("userinfo", account))

    assert reply.data.id == account["id"]
    assert reply.data.real_name == account["realName"]
    assert reply.data.phone_no == account["phoneNo"]
    assert reply.data.birth_year == int(account["birthday"][:4])
    assert reply.data.addresses[0].usage_type == account["addresses"][0]["usageType"]


def test_userinfo_reply_rejects_empty_account() -> None:
    # UserinfoWebMessageHandler 沒有帳號時回傳 []
    with pytest.raises(ValidationError, match="沒有回傳台北通帳號資料"):
        UserinfoReply.model_validate(_reply("userinfo", []))


def test_userinfo_reply_rejects_other_name() -> None:
    account = json.loads(MOCK_ACCOUNT.read_text(encoding="utf-8"))["data"]
    with pytest.raises(ValidationError):
        UserinfoReply.model_validate(_reply("location", account))


def test_location_reply_parses_geolocator_position() -> None:
    # geolocator Position.toJson() 的鍵
    position = {
        "longitude": 121.5654,
        "latitude": 25.033,
        "timestamp": 1762500000000,
        "accuracy": 5.0,
        "altitude": 10.0,
        "altitude_accuracy": 1.0,
        "floor": None,
        "heading": 0.0,
        "heading_accuracy": 0.0,
        "speed": 0.0,
        "speed_accuracy": 0.0,
        "is_mocked": False,
        "vertical_speed": 0.0,
        "vertical_speed_accuracy": 0.0,
        "has_accuracy": True,
    }
    reply = LocationReply.model_validate(_reply("location", position))
    assert reply.data is not None
    assert reply.data.latitude == 25.033


def test_location_reply_failure_becomes_none() -> None:
    # LocationMessageHandler 定位失敗時回傳 []
    assert LocationReply.model_validate(_reply("location", [])).data is None


def test_qr_code_scan_reply() -> None:
    assert QRCodeScanReply.model_validate(_reply("qr_code_scan", "abc")).data == "abc"
    # 使用者取消掃描時 Get.back() 沒有 result
    assert QRCodeScanReply.model_validate(_reply("qr_code_scan", None)).data is None


def test_push_token_reply() -> None:
    reply = PushTokenReply.model_validate(_reply("push_token", {"token": "t", "platform": "ios"}))
    assert reply.data.token == "t"


def test_phone_call_message_is_tel_safe() -> None:
    # PhoneCallMessageHandler 組成 tel://{data}
    msg = PhoneCallMessage.to("0932-166 777")
    assert msg.model_dump() == {"name": "phone_call", "data": "0932166777"}
    with pytest.raises(ValidationError):
        PhoneCallMessage.to("abc")


def test_launch_map_message() -> None:
    msg = LaunchMapMessage.to_address("臺北市大安區仁愛路四段10號")
    assert msg.name == "launch_map"
    assert msg.data.startswith("https://")


def test_notify_message_avoids_subscription_keywords() -> None:
    # NotifyMessageHandler 看到「已訂閱…」會改動訂閱清單
    NotifyMessage(data={"title": "吃藥", "content": "吃藥時間到囉"})
    with pytest.raises(ValidationError):
        NotifyMessage(data={"title": "x", "content": "已訂閱吃藥提醒"})
