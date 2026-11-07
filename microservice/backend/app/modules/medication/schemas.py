import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.integrations.townpass.messages import QRCodeScanReply
from app.modules.medication.models import Frequency, MealTiming, MedicationStatus, SlotKey


class RxQrPayload(BaseModel):
    """藥袋 QR 的內容（規格書 §8.1），鍵名精簡以縮小 QR。"""

    v: Literal[1]
    t: Literal["rx"]
    hosp: str
    dept: str
    dr: str
    date: dt.date
    days: int = Field(gt=0)
    lic: str | None = None
    name: str
    use: str
    qty: Decimal = Field(gt=0, max_digits=3, decimal_places=1)
    freq: Frequency
    meal: MealTiming


class MedicationDraft(BaseModel):
    """確認畫面顯示、確認後送回加入的內容。"""

    name: str = Field(max_length=128)
    license_no: str | None = Field(default=None, max_length=64)
    purpose: str = Field(max_length=128)
    dose_qty: Decimal = Field(gt=0, max_digits=3, decimal_places=1)
    frequency: Frequency
    meal_timing: MealTiming
    start_date: dt.date
    days: int = Field(gt=0)
    hospital: str
    department: str
    doctor: str


class WarningType(StrEnum):
    SAME_INGREDIENT = "same_ingredient"


class MedicationWarning(BaseModel):
    type: WarningType
    with_number: int  # 和幾號藥成分相同
    message: str = "這兩包好像是同一種藥，請問藥師"


class QrPreviewIn(QRCodeScanReply):
    """App 對 { name: 'qr_code_scan' } 的回覆，前端原封不動送來。"""


class QrPreviewOut(BaseModel):
    draft: MedicationDraft
    slots: list[SlotKey]
    warnings: list[MedicationWarning]


class MedicationCreate(MedicationDraft):
    pass


class MedicationUpdate(BaseModel):
    purpose: str | None = Field(default=None, max_length=128)
    dose_qty: Decimal | None = Field(default=None, gt=0, max_digits=3, decimal_places=1)
    frequency: Frequency | None = None
    meal_timing: MealTiming | None = None
    days: int | None = Field(default=None, gt=0)


class MedicationOut(MedicationDraft):
    id: UUID
    number: int
    slots: list[SlotKey]
    days_left: int
    status: MedicationStatus


class MedicationCreated(BaseModel):
    medication: MedicationOut
    warnings: list[MedicationWarning]
    message: str  # 「請在藥袋上寫上大大的 N」


class TimeSlotItem(BaseModel):
    slot_key: SlotKey
    time: dt.time


class TimeSlotsUpdate(BaseModel):
    slots: list[TimeSlotItem] = Field(min_length=1, max_length=len(SlotKey))


class DoseItem(BaseModel):
    number: int
    name: str
    qty: Decimal


class NextDoseOut(BaseModel):
    slot_key: SlotKey
    at: dt.datetime
    items: list[DoseItem]
