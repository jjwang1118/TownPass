import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field

from app.integrations.townpass.messages import PhoneCallMessage
from app.modules.emergency_card.models import ConsentType, Gender
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
    chronic_conditions: list[str] = []
    allergies: list[Allergy] = []
    hospital: str = "臺北市立聯合醫院"


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    relation: str = Field(min_length=1, max_length=20)
    phone: str


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
    accessed_at: dt.datetime


class CardCodeOut(BaseModel):
    code: str
    qr_url: str  # QR 內容


class CardOut(BaseModel):
    """長輩、家人檢視。"""

    title: str
    birth_year: int | None
    gender: Gender | None
    current_medications: list[DoseItem]  # 由藥區帶入
    chronic_conditions: list[str]
    allergies: list[Allergy]
    contacts: list[ContactOut]
    hospital: str
    code: CardCodeOut | None
    access_logs: list[AccessLogOut]
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


class CommonItemsOut(BaseModel):
    chronic_conditions: list[str]
    allergies: list[Allergy]
