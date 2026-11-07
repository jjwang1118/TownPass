import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.integrations.townpass.messages import QRCodeScanReply
from app.modules.medication.models import Frequency, MealTiming, MedicationStatus, SlotKey, StopReason

# 一次幾顆，支援半顆。內部用 Decimal 避免誤差，JSON 輸出為數字（1、0.5）
Qty = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class RxQrPayload(BaseModel):
    """藥袋 QR 的內容（規格書 §8.1），鍵名精簡以縮小 QR。"""

    model_config = ConfigDict(extra="forbid")

    v: Literal[1]
    t: Literal["rx"]
    hosp: str = Field(min_length=1, max_length=64)
    dept: str = Field(min_length=1, max_length=64)
    dr: str = Field(min_length=1, max_length=64)
    date: dt.date
    days: int = Field(gt=0, le=365)
    lic: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    use: str = Field(min_length=1, max_length=128)
    qty: Qty = Field(gt=0, max_digits=3, decimal_places=1)
    freq: Frequency
    meal: MealTiming


class MedicationDraft(BaseModel):
    """確認畫面顯示的內容；長輩核對後原樣送回 POST /medications 加入。"""

    name: str = Field(min_length=1, max_length=128)
    license_no: str | None = Field(default=None, max_length=64)
    purpose: str = Field(min_length=1, max_length=128)
    dose_qty: Qty = Field(gt=0, max_digits=3, decimal_places=1)
    frequency: Frequency
    meal_timing: MealTiming
    start_date: dt.date
    days: int = Field(gt=0, le=365)
    hospital: str = Field(min_length=1, max_length=64)
    department: str = Field(min_length=1, max_length=64)
    doctor: str = Field(min_length=1, max_length=64)


class WarningType(StrEnum):
    SAME_INGREDIENT = "same_ingredient"


class MedicationWarning(BaseModel):
    """只標示，不做醫療判斷。"""

    type: WarningType
    with_number: int  # 和幾號藥成分相同
    message: str


class TimeSlotItem(BaseModel):
    slot_key: SlotKey
    label: str  # 例如「早餐飯後」
    time: dt.time


class QrPreviewIn(QRCodeScanReply):
    """App 對 { name: 'qr_code_scan' } 的回覆，前端原封不動送來。"""


class QrPreviewOut(BaseModel):
    draft: MedicationDraft
    frequency_label: str  # 例如「一天三次」
    meal_timing_label: str  # 例如「飯後」
    slots: list[TimeSlotItem]  # 加入後會在這些時段提醒
    warnings: list[MedicationWarning]


class MedicationCreate(MedicationDraft):
    pass


class MedicationUpdate(BaseModel):
    purpose: str | None = Field(default=None, min_length=1, max_length=128)
    dose_qty: Qty | None = Field(default=None, gt=0, max_digits=3, decimal_places=1)
    frequency: Frequency | None = None
    meal_timing: MealTiming | None = None
    start_date: dt.date | None = None
    days: int | None = Field(default=None, gt=0, le=365)


class MedicationStop(BaseModel):
    reason: StopReason  # 吃完了，或醫生說不用吃了


class MedicationOut(MedicationDraft):
    id: UUID
    number: int  # 藥袋上的大編號
    frequency_label: str
    meal_timing_label: str
    slots: list[TimeSlotItem]  # 例如 飯後 08:00、18:00
    run_out_date: dt.date
    days_left: int
    status: MedicationStatus
    stop_reason: StopReason | None
    speech_text: str  # 「念給我聽」的國語朗讀稿；藥名有中文就念中文，只有英文就念原文
    speech_text_en: str  # 英文朗讀稿（給外籍看護）；科別、用途、稱呼依對照表翻成英文，查不到就不念


class MedicationCreated(BaseModel):
    medication: MedicationOut
    warnings: list[MedicationWarning]
    message: str  # 「請在藥袋上寫上大大的 N」


class TimeSlotUpdateItem(BaseModel):
    slot_key: SlotKey
    time: dt.time


class TimeSlotsUpdate(BaseModel):
    slots: list[TimeSlotUpdateItem] = Field(min_length=1, max_length=len(SlotKey))


class DoseItem(BaseModel):
    number: int
    name: str
    qty: Qty


class NextDoseOut(BaseModel):
    slot_key: SlotKey
    label: str
    at: dt.datetime  # 台北時間
    is_today: bool
    items: list[DoseItem]


class LastVisit(BaseModel):
    """最近一次開藥的院區、科別、醫師，給回診預約帶入。"""

    hospital: str
    department: str
    doctor: str
    date: dt.date
