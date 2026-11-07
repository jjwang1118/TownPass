"""城市通 App 與微服務網頁之間的訊息格式。

依據《城市通入門指引》第 03 章「App 與微服務溝通」與 App 原始碼
lib/util/web_message_handler/：

1. 網頁送出：window.flutterObject.postMessage(JSON.stringify({ name, data }))
2. App 由 TPWebMessageListener 依 name 找到 TPWebMessageHandler 處理
3. App 回覆：replyWebMessage() 包成 { name, data } 的 JSON 字串
4. 網頁收到：JSON.parse(event.data)

後端不直接和 App 溝通。規則如下：
- 「App → 後端」：前端把 App 的回覆 JSON.parse 後，原封不動放進 request body。
  本檔的 *Reply 類別逐欄對照 App 實際回傳的格式。
- 「後端 → App」：後端在回應中附上完整的 { name, data }，前端直接
  postMessage(JSON.stringify(...)) 給 App。本檔的 *Message 類別即為這些訊息。
"""

import re
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

# ---------------------------------------------------------------------------
# 訊息名稱
# ---------------------------------------------------------------------------


class BuiltinMessageName(StrEnum):
    """App 內建 Handler 的 name（tp_web_message_listener.dart 的 _cachedMessageHandlers）。"""

    USERINFO = "userinfo"
    LAUNCH_MAP = "launch_map"
    PHONE_CALL = "phone_call"
    AGREE_1999 = "1999agree"
    LOCATION = "location"
    DEVICE_INFO = "deviceinfo"
    OPEN_LINK = "open_link"
    NOTIFY = "notify"
    QR_CODE_SCAN = "qr_code_scan"


class CustomMessageName(StrEnum):
    """本服務自行擴充的 Handler name。依指引不可與內建名稱重複。"""

    PUSH_TOKEN = "push_token"


_overlap = {m.value for m in BuiltinMessageName} & {m.value for m in CustomMessageName}
if _overlap:  # pragma: no cover - 定義錯誤時讓程式啟動失敗
    raise RuntimeError(f"自訂 Handler name 與內建名稱重複：{_overlap}")


def _empty_list_to_none(value: Any) -> Any:
    """App 取不到資料時，userinfo、location、deviceinfo 的 data 會回傳 []。"""
    return None if value == [] else value


# ---------------------------------------------------------------------------
# App → 後端：App 回覆的格式
# ---------------------------------------------------------------------------


class _CamelModel(BaseModel):
    """欄位名稱對照 lib/bean/account.dart 的 @JsonKey（駝峰式）。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class TownPassAddress(_CamelModel):
    """lib/bean/account.dart Address。"""

    zip3: int
    city: str
    town: str
    village: str
    street: str
    usage_type: str
    seq: int
    priority: bool


class TownPassAccount(_CamelModel):
    """lib/bean/account.dart Account；內容即 assets/mock_data/account.json 的 data。"""

    id: str
    account: str
    username: str
    real_name: str
    id_no: str  # App 一定會帶；本服務用不到，不儲存
    email: str
    phone_no: str
    birthday: str  # 格式 "YYYY/MM/DD"
    member_type: str
    verify_level: str
    addresses: list[TownPassAddress]
    resident_address: str
    citizen: bool
    native_people: bool
    city_internet_uid: str

    @property
    def birth_year(self) -> int | None:
        match = re.match(r"^(\d{4})/", self.birthday)
        return int(match.group(1)) if match else None


class UserinfoReply(BaseModel):
    """App 對 { name: 'userinfo' } 的回覆。沒有帳號時 data 為 []，視為錯誤。"""

    name: Literal[BuiltinMessageName.USERINFO]
    data: TownPassAccount

    @field_validator("data", mode="before")
    @classmethod
    def _require_account(cls, value: Any) -> Any:
        if value == []:
            raise ValueError("App 沒有回傳台北通帳號資料")
        return value


class GeoPosition(BaseModel):
    """geolocator Position.toJson()（LocationMessageHandler 回傳），欄位為底線式。"""

    model_config = ConfigDict(extra="ignore")

    latitude: float
    longitude: float
    timestamp: int  # 毫秒
    accuracy: float | None = None
    altitude: float | None = None
    altitude_accuracy: float | None = None
    floor: int | None = None
    heading: float | None = None
    heading_accuracy: float | None = None
    speed: float | None = None
    speed_accuracy: float | None = None
    is_mocked: bool = False


class LocationReply(BaseModel):
    """App 對 { name: 'location' } 的回覆。沒有權限或定位失敗時 data 為 []，轉成 None。"""

    name: Literal[BuiltinMessageName.LOCATION]
    data: GeoPosition | None

    @field_validator("data", mode="before")
    @classmethod
    def _empty_to_none(cls, value: Any) -> Any:
        return _empty_list_to_none(value)


class QRCodeScanReply(BaseModel):
    """App 對 { name: 'qr_code_scan' } 的回覆。data 為掃到的字串；使用者取消時為 null。"""

    name: Literal[BuiltinMessageName.QR_CODE_SCAN]
    data: str | None


class PushPlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"


class PushTokenData(BaseModel):
    token: str = Field(min_length=1)
    platform: PushPlatform


class PushTokenReply(BaseModel):
    """自訂 Handler { name: 'push_token' } 的回覆（App 端尚未實作，見規格書 §2.1）。"""

    name: Literal[CustomMessageName.PUSH_TOKEN]
    data: PushTokenData


# ---------------------------------------------------------------------------
# 後端 → App：前端直接 postMessage 的訊息
# ---------------------------------------------------------------------------


class PhoneCallMessage(BaseModel):
    """PhoneCallMessageHandler 會組成 tel://{data}，所以只保留數字與開頭的 +。"""

    name: Literal[BuiltinMessageName.PHONE_CALL] = BuiltinMessageName.PHONE_CALL
    data: str

    @field_validator("data")
    @classmethod
    def _digits_only(cls, value: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", value)
        if not re.fullmatch(r"\+?\d{3,15}", cleaned):
            raise ValueError("電話號碼格式不正確")
        return cleaned

    @classmethod
    def to(cls, phone: str) -> "PhoneCallMessage":
        return cls(data=phone)


class LaunchMapMessage(BaseModel):
    """LaunchMapMessageHandler 以 data 為網址開啟地圖。"""

    name: Literal[BuiltinMessageName.LAUNCH_MAP] = BuiltinMessageName.LAUNCH_MAP
    data: str

    @classmethod
    def to_address(cls, address: str) -> "LaunchMapMessage":
        return cls(data=f"https://www.google.com/maps/search/?api=1&query={quote(address)}")


class NotifyData(BaseModel):
    title: str
    content: str

    @field_validator("content")
    @classmethod
    def _avoid_subscription_keywords(cls, value: str) -> str:
        # NotifyMessageHandler 看到「已訂閱…」「已取消訂閱…」會改動 App 的訂閱清單
        if re.search(r"已(取消)?訂閱.", value):
            raise ValueError("通知內容不可包含「已訂閱」或「已取消訂閱」")
        return value


class NotifyMessage(BaseModel):
    """NotifyMessageHandler 顯示本機通知，data 為 { title, content }。"""

    name: Literal[BuiltinMessageName.NOTIFY] = BuiltinMessageName.NOTIFY
    data: NotifyData
