import datetime as dt
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.integrations.townpass.messages import PhoneCallMessage
from app.modules.emergency_card.models import AccessMethod, ConsentType, Gender
from app.modules.emergency_card.rules import DISCLAIMER
from app.modules.medication.schemas import DoseItem

MAX_CONTACTS = 2


class AllergyType(StrEnum):
    DRUG = "drug"
    FOOD = "food"


class Allergy(BaseModel):
    type: AllergyType
    name: str = Field(min_length=1, max_length=32)


class ConsentCreate(BaseModel):
    type: ConsentType = ConsentType.HEALTH_DATA


class ConsentOut(BaseModel):
    type: ConsentType
    granted_at: dt.datetime


class CardUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=20, examples=["陳阿嬤"])
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    gender: Gender | None = None
    chronic_conditions: list[str] = Field(default=[], max_length=20)
    allergies: list[Allergy] = Field(default=[], max_length=20)
    hospital: str = Field(default="臺北市立聯合醫院", min_length=1, max_length=64)

    @field_validator("chronic_conditions")
    @classmethod
    def _clean(cls, items: list[str]) -> list[str]:
        cleaned = [i.strip() for i in items if i.strip()]
        if any(len(i) > 32 for i in cleaned):
            raise ValueError("每個項目最多 32 字")
        return list(dict.fromkeys(cleaned))  # 去除重複，保留順序


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    relation: str = Field(min_length=1, max_length=20)
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone_for_app(cls, value: str) -> str:
        # 和 App 的 phone_call 相同規則：只保留數字與開頭的 +
        return PhoneCallMessage.to(value).data


class ContactsUpdate(BaseModel):
    contacts: list[ContactIn] = Field(max_length=MAX_CONTACTS)


class ContactOut(BaseModel):
    name: str
    relation: str
    phone: str
    call: PhoneCallMessage  # 前端直接 postMessage(JSON.stringify(call)) 撥號


class AccessLogOut(BaseModel):
    responder_name: str
    responder_unit: str
    method: AccessMethod  # 掃 QR 或輸入卡號
    latitude: Decimal | None
    longitude: Decimal | None
    accessed_at: dt.datetime


class CardCodeOut(BaseModel):
    code: str  # 印在貼紙上，QR 掃不到時輸入
    qr_url: str  # QR 內容；用於敬老卡背面貼紙、手機鎖定畫面桌布


class CardOut(BaseModel):
    """長輩、家人檢視。"""

    title: str
    birth_year: int | None
    gender: Gender | None
    current_medications: list[DoseItem]  # 由藥區自動帶入
    chronic_conditions: list[str]
    allergies: list[Allergy]
    contacts: list[ContactOut]
    hospital: str
    code: CardCodeOut | None  # 撤回同意後為 null
    has_consent: bool
    access_logs: list[AccessLogOut]  # 新的在前
    updated_at: dt.datetime


class ResponderCardOut(BaseModel):
    """救護人員檢視，欄位順序即顯示順序：過敏 → 正在吃的藥 → 慢性病 → 緊急聯絡人。"""

    title: str
    birth_year: int | None
    gender: Gender | None
    allergies: list[Allergy]
    current_medications: list[DoseItem]
    chronic_conditions: list[str]
    contacts: list[ContactOut]
    hospital: str
    disclaimer: str = DISCLAIMER
    close_at: dt.datetime  # 畫面自動關閉並清除資料的時間（查詢後 30 分鐘）


class CommonItemsOut(BaseModel):
    chronic_conditions: list[str]
    allergies: list[Allergy]
