"""展示用 API，只在 DEMO_MODE 掛載，正式版移除（規格書 §11.2）。

Demo 時不用等到真正的時間，立即觸發提醒與通知。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.deps import CurrentUserId, SessionDep
from app.modules.reminder.schemas import ReminderOut
from app.modules.reminder.service import ReminderService

router = APIRouter(prefix="/demo", tags=["demo"])

ElderId = Annotated[UUID, Query()]


def get_service(session: SessionDep) -> ReminderService:
    return ReminderService(session)


Service = Annotated[ReminderService, Depends(get_service)]


class RefillTriggered(BaseModel):
    numbers: list[int]


@router.post("/trigger/reminder", response_model=ReminderOut)
async def trigger_reminder(elder_id: ElderId, user_id: CurrentUserId, service: Service) -> ReminderOut:
    """立即提醒今天第一個有藥的時段。"""
    return await service.demo_trigger_reminder(user_id, elder_id)


@router.post("/trigger/no-response", response_model=ReminderOut)
async def trigger_no_response(elder_id: ElderId, user_id: CurrentUserId, service: Service) -> ReminderOut:
    """立即當作 3 次沒回應，通知家人。"""
    return await service.demo_trigger_no_response(user_id, elder_id)


@router.post("/trigger/refill", response_model=RefillTriggered)
async def trigger_refill(elder_id: ElderId, user_id: CurrentUserId, service: Service) -> RefillTriggered:
    """立即發回診提醒。"""
    return RefillTriggered(numbers=await service.demo_trigger_refill(user_id, elder_id))
