"""展示用 API，只在 DEMO_MODE 掛載，正式版移除（規格書 §11.2）。"""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId
from app.core.errors import NotImplementedYet

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/trigger/reminder", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_reminder(elder_id: UUID, _: CurrentUserId) -> None:
    raise NotImplementedYet()


@router.post("/trigger/no-response", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_no_response(elder_id: UUID, _: CurrentUserId) -> None:
    raise NotImplementedYet()


@router.post("/trigger/refill", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_refill(elder_id: UUID, _: CurrentUserId) -> None:
    raise NotImplementedYet()
