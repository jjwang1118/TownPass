import datetime as dt
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.reminder.schemas import ReminderOut
from app.modules.reminder.service import ReminderService

router = APIRouter(tags=["reminder"])


def get_service(session: SessionDep) -> ReminderService:
    return ReminderService(session)


Service = Annotated[ReminderService, Depends(get_service)]


@router.get("/reminders/{event_id}", response_model=ReminderOut)
async def get_reminder(event_id: UUID, user_id: CurrentUserId, service: Service) -> ReminderOut:
    return await service.get(user_id, event_id)


@router.get("/elders/{elder_id}/reminders", response_model=list[ReminderOut])
async def list_reminders(
    elder_id: UUID, user_id: CurrentUserId, service: Service, date: Annotated[dt.date, Query()]
) -> list[ReminderOut]:
    return await service.list_by_date(user_id, elder_id, date)


@router.post("/elders/{elder_id}/nudge", status_code=status.HTTP_204_NO_CONTENT)
async def nudge(elder_id: UUID, user_id: CurrentUserId, service: Service) -> None:
    await service.nudge(user_id, elder_id)
