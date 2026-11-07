import datetime as dt
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.integrations.townpass.messages import LocationReply, QRCodeScanReply


class LoginIn(BaseModel):
    """UI R01：所屬單位（下拉選單）、人員編號、密碼皆必填。"""

    unit: str = Field(examples=["大安分隊"])
    staff_no: str = Field(examples=["A12345"])
    password: str


class UnitsOut(BaseModel):
    agency: str  # 臺北市政府消防局
    units: list[str]  # 各分隊（範例名稱）


class ResponderTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: dt.datetime  # 12 小時（一個勤務班）
    name: str
    unit: str
    staff_no: str
    title: str


class LookupIn(BaseModel):
    """qr 與 code 擇一：

    - qr：App 對 { name: 'qr_code_scan' } 的回覆，原封不動送來
    - code：QR 掃不到時手動輸入的卡號
    - location：App 對 { name: 'location' } 的回覆，原封不動送來（取不到時可省略）
    """

    qr: QRCodeScanReply | None = None
    code: str | None = Field(default=None, examples=["TPE-7K3Q-9X2M"])
    location: LocationReply | None = None

    @model_validator(mode="after")
    def _one_of_qr_or_code(self) -> Self:
        has_qr = self.qr is not None and self.qr.data is not None
        if has_qr == (self.code is not None):
            raise ValueError("qr 與 code 必須擇一提供")
        return self
