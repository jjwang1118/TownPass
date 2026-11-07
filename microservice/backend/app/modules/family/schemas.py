import datetime as dt
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.integrations.townpass.messages import QRCodeScanReply


class InviteOut(BaseModel):
    code: str
    qr_url: str  # 邀請 QR 的內容
    expires_at: dt.datetime


class BindingCreate(BaseModel):
    """qr 與 code 擇一：

    - qr：家人掃邀請 QR 時，App 對 { name: 'qr_code_scan' } 的回覆，原封不動送來
    - code：手動輸入的 6 位數邀請碼
    """

    qr: QRCodeScanReply | None = None
    code: str | None = Field(default=None, examples=["123456"])
    relation_label: str = Field(min_length=1, max_length=20, examples=["媽媽"])

    @model_validator(mode="after")
    def _one_of_qr_or_code(self) -> Self:
        has_qr = self.qr is not None and self.qr.data is not None
        if has_qr == (self.code is not None):
            raise ValueError("qr 與 code 必須擇一提供")
        return self

    @property
    def raw_code(self) -> str:
        return self.code if self.code is not None else self.qr.data  # type: ignore[union-attr]


class BindingUpdate(BaseModel):
    notify_on_ack: bool | None = None
    relation_label: str | None = Field(default=None, min_length=1, max_length=20)


class BindingOut(BaseModel):
    id: UUID
    elder_id: UUID
    elder_name: str
    elder_phone: str  # 家屬「打電話給長輩」
    family_id: UUID
    family_name: str
    relation_label: str
    notify_on_ack: bool
    can_setup: bool  # 還能做初始設定
    created_at: dt.datetime
