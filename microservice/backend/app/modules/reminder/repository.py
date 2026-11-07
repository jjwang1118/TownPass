import datetime as dt
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medication.models import SlotKey
from app.modules.reminder.models import RefillNotice, ReminderEvent


class ReminderRepository:
    """reminder_events、refill_notices 的存取。

    排程可能同時被呼叫兩次，所以「建立」用一條 SQL 完成，只有成功寫入的那一次會發出推播。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, event_id: UUID) -> ReminderEvent | None:
        return await self.session.get(ReminderEvent, event_id)

    async def create_event(
        self,
        *,
        elder_id: UUID,
        slot_key: SlotKey,
        scheduled_date: dt.date,
        scheduled_at: dt.datetime,
        groups: list[dict[str, Any]],
        now: dt.datetime,
    ) -> ReminderEvent | None:
        """當天這個時段已經有提醒時回傳 None。"""
        stmt = (
            insert(ReminderEvent)
            .values(
                elder_id=elder_id,
                slot_key=slot_key,
                scheduled_date=scheduled_date,
                scheduled_at=scheduled_at,
                groups=groups,
                pushed_at=now,
            )
            .on_conflict_do_nothing(index_elements=["elder_id", "slot_key", "scheduled_date"])
            .returning(ReminderEvent)
        )
        return await self.session.scalar(stmt)

    async def list_by_date(self, elder_id: UUID, day: dt.date) -> list[ReminderEvent]:
        stmt = (
            select(ReminderEvent)
            .where(ReminderEvent.elder_id == elder_id, ReminderEvent.scheduled_date == day)
            .order_by(ReminderEvent.scheduled_at)
        )
        return list(await self.session.scalars(stmt))

    async def get_by_day_slot(self, elder_id: UUID, slot_key: SlotKey, day: dt.date) -> ReminderEvent | None:
        stmt = select(ReminderEvent).where(
            ReminderEvent.elder_id == elder_id,
            ReminderEvent.slot_key == slot_key,
            ReminderEvent.scheduled_date == day,
        )
        return await self.session.scalar(stmt)

    async def latest(self, elder_id: UUID) -> ReminderEvent | None:
        stmt = (
            select(ReminderEvent)
            .where(ReminderEvent.elder_id == elder_id)
            .order_by(ReminderEvent.scheduled_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def create_refill_notice(self, elder_id: UUID, run_out_date: dt.date, letters: list[str]) -> bool:
        """記錄回診提醒；已經發過回傳 False。"""
        stmt = (
            insert(RefillNotice)
            .values(elder_id=elder_id, run_out_date=run_out_date, letters=letters)
            .on_conflict_do_nothing(index_elements=["elder_id", "run_out_date"])
            .returning(RefillNotice.elder_id)
        )
        return await self.session.scalar(stmt) is not None
