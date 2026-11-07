from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.notification.schemas import DeviceRegisterIn
from app.modules.notification.service import NotificationService

router = APIRouter(prefix="/devices", tags=["notification"])


def get_service(session: SessionDep) -> NotificationService:
    return NotificationService(session)


Service = Annotated[NotificationService, Depends(get_service)]


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def register_device(body: DeviceRegisterIn, user_id: CurrentUserId, service: Service) -> None:
    """body 為 App 對 { name: 'push_token' } 的回覆。"""
    await service.register_device(user_id, body.data)


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(token: str, user_id: CurrentUserId, service: Service) -> None:
    await service.unregister_device(user_id, token)
