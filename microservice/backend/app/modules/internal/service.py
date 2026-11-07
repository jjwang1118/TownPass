from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.modules.reminder.schemas import TickResult
from app.modules.reminder.service import ReminderService


class TickService:
    """排程入口，只負責依序呼叫各模組；每項工作都必須可重複執行而不重複發送。"""

    def __init__(self, session: AsyncSession) -> None:
        self.reminders = ReminderService(session)

    async def run(self) -> TickResult:
        # TODO: 回診預約提醒（前一天 18:00、當天 08:00），等 appointment 模組完成後加入
        return await self.reminders.tick(clock.now())
