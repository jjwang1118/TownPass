import datetime as dt
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.integrations.townpass.messages import PhoneCallMessage
from app.modules.emergency_card.models import (
    AccessMethod,
    BloodType,
    ConsentType,
    Gender,
)
from app.modules.emergency_card.rules import DISCLAIMER
from app.modules.medication.schemas import DoseItem


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


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    relation: str = Field(min_length=1, max_length=20)
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone_for_app(cls, value: str) -> str:
        # 和 App 的 phone_call 相同規則：只保留數字與開頭的 +
        return PhoneCallMessage.to(value).data


class CardUpdate(BaseModel):
    """UI E14：姓名、出生年月日、一位緊急聯絡人必填。目前用藥由藥單自動帶入，不能手動編輯。"""

    name: str = Field(min_length=1, max_length=32, examples=["王美玉"])
    birth_date: dt.date = Field(examples=["1948-05-12"])
    gender: Gender | None = None
    blood_type: BloodType = BloodType.UNKNOWN
    chronic_conditions: list[str] = Field(default=[], max_length=20)
    allergies: list[Allergy] = Field(default=[], max_length=20)  # 藥物過敏、食物過敏
    contact: ContactIn

    @field_validator("chronic_conditions")
    @classmethod
    def _clean(cls, items: list[str]) -> list[str]:
        cleaned = [i.strip() for i in items if i.strip()]
        if any(len(i) > 32 for i in cleaned):
            raise ValueError("每個項目最多 32 字")
        return list(dict.fromkeys(cleaned))  # 去除重複，保留順序


class ContactOut(BaseModel):
    name: str
    relation: str
    phone: str
    call: PhoneCallMessage  # 前端直接 postMessage(JSON.stringify(call)) 撥號


class AccessLogOut(BaseModel):
    responder_name: str
    responder_unit: str
    responder_staff_no: str | None  # 人員編號
    method: AccessMethod  # 掃 QR 或輸入卡號
    latitude: Decimal | None
    longitude: Decimal | None
    accessed_at: dt.datetime


class CardCodeOut(BaseModel):
    code: str  # 印在貼紙上，QR 掃不到時輸入
    qr_url: str  # QR 內容；用於敬老卡背面貼紙、手機鎖定畫面桌布


class CardOut(BaseModel):
    """長輩、家人檢視（UI E13、F06）。"""

    name: str
    birth_date: dt.date | None
    age: int | None  # 例如 78
    gender: Gender | None
    blood_type: BloodType
    contact: ContactOut | None  # 緊急聯絡人（一位）
    chronic_conditions: list[str]  # 本人填寫
    allergies: list[Allergy]  # 本人填寫
    current_medications: list[DoseItem]  # 來自藥單，例如 A1
    code: CardCodeOut | None  # 撤回同意後為 null
    has_consent: bool
    access_logs: list[AccessLogOut]  # 新的在前
    updated_at: dt.datetime


class ResponderCardOut(BaseModel):
    """救護人員檢視（UI R03）：只回傳必要欄位，不含常去醫院與病歷號。"""

    name: str
    age: int | None
    gender: Gender | None
    blood_type: BloodType
    contact: ContactOut | None  # 「撥打 陳小華（女兒）」
    chronic_conditions: list[str]
    allergies: list[Allergy]
    current_medications: list[DoseItem]
    disclaimer: str = DISCLAIMER
    close_at: dt.datetime  # 畫面自動關閉並清除資料的時間（查詢後 30 分鐘）


class CommonItemsOut(BaseModel):
    chronic_conditions: list[str]
    allergies: list[Allergy]
