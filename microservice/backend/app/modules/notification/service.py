from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.fcm.client import PushMessage, get_pusher
from app.integrations.townpass.messages import PushTokenData
from app.modules.notification.models import DeviceToken
from app.modules.notification.repository import DeviceTokenRepository
from app.modules.notification.schemas import PushType


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.devices = DeviceTokenRepository(session)

    async def register_device(self, user_id: UUID, data: PushTokenData) -> None:
        """同一個 token 換人登入時改綁到新使用者。"""
        device = await self.devices.get_by_token(data.token)
        if device is None:
            await self.devices.add(DeviceToken(user_id=user_id, token=data.token, platform=data.platform))
        else:
            device.user_id = user_id
            device.platform = data.platform
        await self.session.commit()

    async def unregister_device(self, user_id: UUID, token: str) -> None:
        await self.devices.delete_token(user_id, token)
        await self.session.commit()

    async def push(
        self, user_ids: list[UUID], type: PushType, title: str, body: str, data: dict[str, str] | None = None
    ) -> None:
        """其他模組要推播時呼叫。不 commit，交由呼叫端的交易決定。"""
        tokens = await self.devices.list_tokens(user_ids)
        if tokens:
            await get_pusher().send(
                tokens, PushMessage(title=title, body=body, data={"type": type.value, **(data or {})})
            )
