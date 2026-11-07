from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.modules.reminder.service import ReminderService


class TickResult(BaseModel):
    created: int
    repushed: int
    escalated: int


class TickService:
    """排程入口，只負責依序呼叫各模組；每項工作都必須可重複執行而不重複發送。"""

    def __init__(self, session: AsyncSession) -> None:
        self.reminders = ReminderService(session)

    async def run(self) -> TickResult:
        now = clock.now()
        # TODO: 回診提醒（每天 09:00）、預約提醒（前一天 18:00、當天 08:00）
        return TickResult(
            created=await self.reminders.create_due_events(now),
            repushed=await self.reminders.repush_unacked(now),
            escalated=await self.reminders.escalate_no_response(now),
        )
