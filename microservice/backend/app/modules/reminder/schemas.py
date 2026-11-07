import datetime as dt
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from app.modules.medication.models import SlotKey
from app.modules.medication.schemas import DoseItem


class ReminderStatus(StrEnum):
    PENDING = "pending"  # 等待長輩回應
    ACKED = "acked"  # 長輩按了「好，我知道了」
    NO_RESPONSE = "no_response"  # 3 次沒回應，已通知家人


class ReminderOut(BaseModel):
    """提醒畫面（功能規格 1-5）。前端依 items 大字顯示「1 號 → 2 顆」，並朗讀 speech_text。"""

    id: UUID
    elder_id: UUID
    elder_title: str  # 例如「陳阿嬤」
    slot_key: SlotKey
    label: str  # 例如「晚餐飯後」
    scheduled_at: dt.datetime
    items: list[DoseItem]
    speech_text: str  # 國語朗讀稿，不含英文字母；台語由前端用預錄句子拼接
    status: ReminderStatus
    attempts: int
    acked_at: dt.datetime | None
    escalated_at: dt.datetime | None

