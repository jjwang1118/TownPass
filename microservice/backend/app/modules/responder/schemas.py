import datetime as dt
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.integrations.townpass.messages import LocationReply, QRCodeScanReply


class LoginIn(BaseModel):
    account: str = Field(examples=["EMT-001"])
    password: str


class ResponderTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: dt.datetime  # 12 小時（一個勤務班）
    name: str
    unit: str
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
