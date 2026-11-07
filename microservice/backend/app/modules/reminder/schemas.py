import datetime as dt
from uuid import UUID

from pydantic import BaseModel

from app.modules.medication.models import SlotKey
from app.modules.medication.schemas import DoseItem, SlotGroup


class ReminderOut(BaseModel):
    """吃藥提醒（點開推播後的時段用藥詳情）。前端依 groups 顯示，並朗讀 speech_text。"""

    id: UUID
    elder_id: UUID
    elder_name: str
    slot_key: SlotKey
    label: str  # 早上、中午、晚上、睡前
    scheduled_at: dt.datetime
    items: list[DoseItem]
    groups: list[SlotGroup]  # 依藥單分組
    speech_text: str  # 「中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆」
    speech_text_en: str
    pushed_at: dt.datetime  # 推播長輩與家屬的時間
