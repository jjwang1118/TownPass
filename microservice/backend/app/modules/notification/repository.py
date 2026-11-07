from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import DeviceToken


class DeviceTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_token(self, token: str) -> DeviceToken | None:
        result = await self.session.execute(select(DeviceToken).where(DeviceToken.token == token))
        return result.scalar_one_or_none()

    async def list_tokens(self, user_ids: list[UUID]) -> list[str]:
        result = await self.session.execute(select(DeviceToken.token).where(DeviceToken.user_id.in_(user_ids)))
        return list(result.scalars())

    async def add(self, device: DeviceToken) -> DeviceToken:
        self.session.add(device)
        await self.session.flush()
        return device

    async def delete_token(self, user_id: UUID, token: str) -> None:
        await self.session.execute(
            delete(DeviceToken).where(DeviceToken.user_id == user_id, DeviceToken.token == token)
        )
