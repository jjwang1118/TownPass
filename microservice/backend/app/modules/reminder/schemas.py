import datetime as dt
from uuid import UUID

from pydantic import BaseModel

from app.modules.medication.models import SlotKey
from app.modules.medication.schemas import DoseItem


class ReminderOut(BaseModel):
    """提醒畫面資料。語音由前端組成：「{elder_title}，吃藥時間到囉～飯後吃：1 號 2 顆…」"""

    id: UUID
    elder_title: str  # 救命卡上的稱呼，例如「阿嬤」
    slot_key: SlotKey
    scheduled_at: dt.datetime
    items: list[DoseItem]
    attempts: int
    acked_at: dt.datetime | None
    escalated_at: dt.datetime | None
