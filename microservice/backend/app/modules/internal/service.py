from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.modules.appointment.service import AppointmentService
from app.modules.reminder.service import ReminderService


class TickResult(BaseModel):
    created: int  # 新建立並推播的吃藥提醒
    repushed: int  # 重新提醒
    escalated: int  # 通知家人沒有回應
    refill: int  # 回診提醒（藥再 7 天吃完）
    appointment: int  # 預約提醒（前一天、當天）


class TickService:
    """排程入口，只負責依序呼叫各模組；每項工作都必須可重複執行而不重複發送。"""

    def __init__(self, session: AsyncSession) -> None:
        self.reminders = ReminderService(session)
        self.appointments = AppointmentService(session)

    async def run(self) -> TickResult:
        now = clock.now()
        return TickResult(
            created=await self.reminders.create_due_events(now),
            repushed=await self.reminders.repush_unacked(now),
            escalated=await self.reminders.escalate_no_response(now),
            refill=await self.reminders.send_refill_reminders(now),
            appointment=await self.appointments.send_reminders(now),
        )
