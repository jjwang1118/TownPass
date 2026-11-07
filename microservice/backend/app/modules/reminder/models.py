import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, enum_column
from app.modules.medication.models import SlotKey


class ReminderEvent(UUIDPrimaryKey, CreatedAt, Base):
    """每位長輩、每個時段、每天最多一筆，由排程建立，同時推播長輩與所有綁定家屬。"""

    __tablename__ = "reminder_events"
    __table_args__ = (UniqueConstraint("elder_id", "slot_key", "scheduled_date"),)

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    slot_key: Mapped[SlotKey] = mapped_column(enum_column(SlotKey))
    scheduled_date: Mapped[dt.date]  # 台北日期
    scheduled_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    # 快照：依藥單分組的 SlotGroup，避免之後改藥影響紀錄
    groups: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    pushed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class RefillNotice(CreatedAt, Base):
    """回診提醒（藥單再 7 天吃完）的發送紀錄，同一位長輩同一個吃完日只發一次。"""

    __tablename__ = "refill_notices"

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    run_out_date: Mapped[dt.date] = mapped_column(primary_key=True)
    letters: Mapped[list[str]] = mapped_column(JSONB)  # 提醒了哪幾張藥單
