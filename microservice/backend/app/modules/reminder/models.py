import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, enum_column
from app.modules.medication.models import SlotKey


class ReminderEvent(UUIDPrimaryKey, CreatedAt, Base):
    """每位長輩每個時段每天一筆，由 /internal/tick 建立。"""

    __tablename__ = "reminder_events"
    __table_args__ = (UniqueConstraint("elder_id", "slot_key", "scheduled_at"),)

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    slot_key: Mapped[SlotKey] = mapped_column(enum_column(SlotKey))
    scheduled_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    # 快照：[{"number": 1, "name": "…", "qty": 2}]，避免之後改藥影響紀錄
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    last_pushed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    acked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    escalated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
