import datetime as dt
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.integrations.townpass.messages import QRCodeScanReply
from app.modules.medication import rules
from app.modules.medication.models import (
    Frequency,
    MealTiming,
    MedicationStatus,
    PrescriptionSource,
    PrescriptionStatus,
    SlotKey,
    StopReason,
)

# 一次幾顆，支援半顆。內部用 Decimal 避免誤差，JSON 輸出為數字（1、0.5）
Qty = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Confidence = Annotated[float, Field(ge=0, le=1)]
# 什麼時候吃（可複選）：去除重複並依時間排序
Slots = Annotated[list[SlotKey], AfterValidator(rules.sort_slots)]


# ---------- 藥袋 QR（規格書 §8.1） ----------


class RxQrItem(BaseModel):
    """v2 藥袋 QR 裡的一個藥。when 與 freq 擇一（when 優先）。"""

    model_config = ConfigDict(extra="forbid")

    lic: str | None = Field(default=None, max_length=64)  # 健保藥品代號
    name: str = Field(min_length=1, max_length=128)
    mg: str | None = Field(default=None, max_length=32)  # 劑量，例如「5 毫克」
    use: str | None = Field(default=None, max_length=128)
    qty: Qty = Field(gt=0, max_digits=3, decimal_places=1)
    when: list[SlotKey] | None = Field(default=None, min_length=1)
    freq: Frequency | None = None
    meal: MealTiming

    @model_validator(mode="after")
    def _when_or_freq(self) -> Self:
        if not self.when and self.freq is None:
            raise ValueError("when 與 freq 至少要有一個")
        return self


class RxQrPayload(BaseModel):
    """v2：一個藥袋（一張藥單）一個 QR，可以有多個藥。鍵名精簡以縮小 QR。"""

    model_config = ConfigDict(extra="forbid")

    v: Literal[2]
    t: Literal["rx"]
    hosp: str = Field(min_length=1, max_length=64)
    dept: str = Field(min_length=1, max_length=64)
    dr: str = Field(min_length=1, max_length=64)
    date: dt.date
    days: int = Field(gt=0, le=365)
    items: list[RxQrItem] = Field(min_length=1, max_length=20)


class RxQrPayloadV1(BaseModel):
    """舊版（一個 QR 一個藥），仍可掃描。"""

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
    meal: Literal["before", "after", "bedtime"]


class QrPreviewIn(QRCodeScanReply):
    """App 對 { name: 'qr_code_scan' } 的回覆，前端原封不動送來。"""


# ---------- 拍照辨識（手機上的模型整理出欄位，後端比對健保資料並打分數） ----------


class PhotoItemIn(BaseModel):
    """手機辨識出的一個藥；看不出來的欄位留空。confidence 為手機模型對各欄位的把握（0～1，可省略）。"""

    name: str | None = Field(default=None, max_length=128)
    license_no: str | None = Field(default=None, max_length=64)  # 藥袋上印的健保碼
    strength: str | None = Field(default=None, max_length=32)
    purpose: str | None = Field(default=None, max_length=128)
    dose_qty: Qty | None = Field(default=None, gt=0, max_digits=3, decimal_places=1)
    slots: list[SlotKey] | None = None
    frequency: Frequency | None = None
    meal_timing: MealTiming | None = None
    confidence: dict[str, Confidence] = Field(default={}, examples=[{"name": 0.6, "dose_qty": 0.95}])


class PhotoIn(BaseModel):
    """拍藥袋照片後，App 用裝置端模型整理出的藥單欄位（後端不做影像辨識，規格書 §1.3）。"""

    hospital: str | None = Field(default=None, max_length=64)
    department: str | None = Field(default=None, max_length=64)
    doctor: str | None = Field(default=None, max_length=64)
    visit_date: dt.date | None = None
    days: int | None = Field(default=None, gt=0, le=365)
    items: list[PhotoItemIn] = Field(min_length=1, max_length=20)
    confidence: dict[str, Confidence] = Field(default={}, examples=[{"hospital": 0.9, "days": 0.7}])


# ---------- 藥單草稿（三條路徑共用）與加入 ----------


class DraftItem(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    license_no: str | None = Field(default=None, max_length=64)
    strength: str | None = Field(default=None, max_length=32)
    purpose: str | None = Field(default=None, max_length=128)
    dose_qty: Qty = Field(gt=0, max_digits=3, decimal_places=1)
    slots: Slots = Field(min_length=1)  # 什麼時候吃（可複選）
    meal_timing: MealTiming
    needs_review: bool = False  # 劑量選「看不清楚／不確定」，加入後標示「待核對」


class PrescriptionDraft(BaseModel):
    """確認藥單畫面的內容；長輩（或幫忙的藥師、家人）核對後送回 POST /prescriptions 加入。"""

    source: PrescriptionSource
    hospital: str | None = Field(default=None, max_length=64)
    department: str | None = Field(default=None, max_length=64)  # 手動新增時可之後補填
    doctor: str | None = Field(default=None, max_length=64)
    visit_date: dt.date
    days: int | None = Field(default=None, gt=0, le=365)  # 拍照看不出來時為 null，加入前必須填
    items: list[DraftItem] = Field(min_length=1, max_length=20)


class PrescriptionCreate(PrescriptionDraft):
    pass


class WarningType(StrEnum):
    SAME_INGREDIENT = "same_ingredient"


class MedicationWarning(BaseModel):
    """只標示，不做醫療判斷。code 和 with_code 成分相同（可能是吃藥中的藥，或同一張藥單的另一個藥）。"""

    type: WarningType
    code: str  # 新加入的藥，例如 C1
    with_code: str  # 成分相同的藥，例如 A1
    message: str


class TimeSlotItem(BaseModel):
    slot_key: SlotKey
    label: str  # 早上、中午、晚上、睡前
    time: dt.time


class Uncertain(BaseModel):
    """拍照辨識沒把握的欄位，畫面用紅框標示。"""

    field: str  # 例如 days、items.1.name
    confidence: float
    message: str


class PreviewItem(BaseModel):
    code: str  # 加入後的編號，例如 A2
    slots: list[TimeSlotItem]
    meal_timing_label: str
    warnings: list[MedicationWarning]
    uncertain: bool  # 「電腦不確定這一項，請照藥袋核對」
    uncertain_fields: list[str]  # 這個藥裡沒把握的欄位，例如 ["name", "strength"]


class ScheduleRow(BaseModel):
    """加入完成頁：四個時段各吃哪幾號（沒有藥的時段 codes 為空）。"""

    slot_key: SlotKey
    label: str
    time: dt.time
    codes: list[str]


class PreviewOut(BaseModel):
    letter: str  # 加入後會配的字母
    draft: PrescriptionDraft
    items: list[PreviewItem]
    uncertain: list[Uncertain]  # 拍照辨識沒把握的欄位；QR、手動為空
    warnings: list[MedicationWarning]
    schedule: list[ScheduleRow]


# ---------- 藥單與藥品 ----------


class MedicationOut(BaseModel):
    id: UUID
    prescription_id: UUID
    letter: str
    seq: int
    code: str  # 例如 A1，長輩看到的大編號
    name: str
    license_no: str | None
    strength: str | None
    purpose: str | None
    dose_qty: Qty
    slots: list[TimeSlotItem]
    meal_timing: MealTiming
    meal_timing_label: str
    needs_review: bool  # 待核對
    status: MedicationStatus
    stop_reason: StopReason | None
    speech_text: str  # 「念給我聽」的國語朗讀稿
    speech_text_en: str  # 英文朗讀稿（給外籍看護）


class PrescriptionOut(BaseModel):
    id: UUID
    letter: str
    source: PrescriptionSource
    hospital: str | None
    department: str | None
    doctor: str | None
    visit_date: dt.date
    days: int
    run_out_date: dt.date
    days_left: int
    status: PrescriptionStatus
    needs_review: bool  # 有待核對的藥
    medications: list[MedicationOut]


class PrescriptionCreated(BaseModel):
    prescription: PrescriptionOut
    warnings: list[MedicationWarning]
    schedule: list[ScheduleRow]
    message: str  # 「請用筆在這個藥袋上寫一個大大的「A」…」


class PrescriptionUpdate(BaseModel):
    """補填或修改藥單資料（例如手動新增後補填科別）。只送要修改的欄位。"""

    hospital: str | None = Field(default=None, min_length=1, max_length=64)
    department: str | None = Field(default=None, min_length=1, max_length=64)
    doctor: str | None = Field(default=None, min_length=1, max_length=64)
    visit_date: dt.date | None = None
    days: int | None = Field(default=None, gt=0, le=365)


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    license_no: str | None = Field(default=None, max_length=64)
    strength: str | None = Field(default=None, max_length=32)
    purpose: str | None = Field(default=None, min_length=1, max_length=128)
    dose_qty: Qty | None = Field(default=None, gt=0, max_digits=3, decimal_places=1)
    slots: Slots | None = Field(default=None, min_length=1)
    meal_timing: MealTiming | None = None
    needs_review: bool | None = None


class MedicationStop(BaseModel):
    reason: StopReason  # 吃完了，或醫生說不用吃了


# ---------- 藥名搜尋 ----------


class StrengthOption(BaseModel):
    label: str  # 例如「5 毫克」
    license_no: str  # 選這個劑量時帶入的健保藥品代號


class DrugSearchItem(BaseModel):
    name: str  # 英文藥名，例如 Norvasc
    name_zh: str | None  # 中文藥名，例如 脈優錠
    ingredient: str | None  # 主成分，例如 AMLODIPINE
    form: str | None  # 劑型
    strengths: list[StrengthOption]  # 只有 1 種時前端自動選好
    common: bool  # 北市聯醫常用藥（模擬）


# ---------- 今天的藥、下一次吃藥 ----------


class DoseItem(BaseModel):
    code: str  # A1
    letter: str
    seq: int
    name: str
    strength: str | None
    qty: Qty
    purpose: str | None
    meal_timing_label: str


class SlotGroup(BaseModel):
    """時段用藥詳情依藥單分組：「B｜新陳代謝科｜中興院區」。"""

    letter: str
    hospital: str | None
    department: str | None
    items: list[DoseItem]


class TodaySlot(BaseModel):
    slot_key: SlotKey
    label: str
    time: dt.time
    items: list[DoseItem]
    groups: list[SlotGroup]
    speech_text: str  # 「中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆」
    speech_text_en: str


class TodayOut(BaseModel):
    """今天四個時段的藥；沒有藥的時段不列出。已過／現在／等一下由前端依時間判斷。"""

    date: dt.date
    slots: list[TodaySlot]


class NextDoseOut(BaseModel):
    slot_key: SlotKey
    label: str
    at: dt.datetime  # 台北時間
    is_today: bool
    items: list[DoseItem]


class LastVisit(BaseModel):
    """最近一張吃藥中藥單的院區、科別、醫師，給回診預約帶入。"""

    letter: str
    hospital: str | None
    department: str | None
    doctor: str | None
    date: dt.date
