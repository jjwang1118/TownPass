from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.modules.appointment.service import AppointmentService
from app.modules.reminder.service import ReminderService


class TickResult(BaseModel):
    created: int  # 新建立並推播的吃藥提醒（長輩與家屬同時）
    refill: int  # 回診提醒（藥單再 7 天吃完）
    appointment: int  # 預約提醒（前一天 18:00）


class TickService:
    """排程入口，只負責依序呼叫各模組；每項工作都必須可重複執行而不重複發送。"""

    def __init__(self, session: AsyncSession) -> None:
        self.reminders = ReminderService(session)
        self.appointments = AppointmentService(session)

    async def run(self) -> TickResult:
        now = clock.now()
        return TickResult(
            created=await self.reminders.create_due_events(now),
            refill=await self.reminders.send_refill_reminders(now),
            appointment=await self.appointments.send_reminders(now),
        )
