import datetime as dt
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotImplementedYet
from app.modules.reminder.repository import ReminderRepository
from app.modules.reminder.schemas import ReminderOut


class ReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReminderRepository(session)

    async def get(self, user_id: UUID, event_id: UUID) -> ReminderOut:
        raise NotImplementedYet()

    async def ack(self, user_id: UUID, event_id: UUID) -> ReminderOut:
        """長輩按「好，我知道了」；依 notify_on_ack 通知家人。"""
        raise NotImplementedYet()

    async def list_by_date(self, user_id: UUID, elder_id: UUID, date: dt.date) -> list[ReminderOut]:
        raise NotImplementedYet()

    async def nudge(self, family_id: UUID, elder_id: UUID) -> None:
        """家人提醒長輩吃藥。"""
        raise NotImplementedYet()

    # ---- 由 /internal/tick 呼叫（規格書 §6.1）----

    async def create_due_events(self, now: dt.datetime) -> int:
        raise NotImplementedYet()

    async def repush_unacked(self, now: dt.datetime) -> int:
        raise NotImplementedYet()

    async def escalate_no_response(self, now: dt.datetime) -> int:
        raise NotImplementedYet()
