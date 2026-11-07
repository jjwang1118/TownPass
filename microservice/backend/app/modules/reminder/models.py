import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, enum_column
from app.modules.medication.models import SlotKey


class ReminderEvent(UUIDPrimaryKey, CreatedAt, Base):
    """每位長輩、每個時段、每天最多一筆，由 /internal/tick 建立。"""

    __tablename__ = "reminder_events"
    # 以台北日期判斷「當天已提醒」；當天改了時段時間也不會重複提醒
    __table_args__ = (UniqueConstraint("elder_id", "slot_key", "scheduled_date"),)

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    slot_key: Mapped[SlotKey] = mapped_column(enum_column(SlotKey))
    scheduled_date: Mapped[dt.date]  # 台北日期
    scheduled_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    # 快照：[{"number": 1, "name": "…", "qty": "2"}]，避免之後改藥影響紀錄
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)  # 已推播次數（最多 3）
    last_pushed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    acked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # 長輩按「好，我知道了」
    escalated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # 已通知家人沒有回應


class RefillNotice(CreatedAt, Base):
    """回診提醒（藥再 7 天吃完）的發送紀錄，同一位長輩同一個吃完日只發一次。"""

    __tablename__ = "refill_notices"

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    run_out_date: Mapped[dt.date] = mapped_column(primary_key=True)
    numbers: Mapped[list[int]] = mapped_column(JSONB)  # 提醒了哪幾號藥
