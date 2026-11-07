from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.responder.models import Responder


class ResponderRepository:
    """responders 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, responder_id: UUID) -> Responder | None:
        return await self.session.get(Responder, responder_id)

    async def get_by_account(self, account: str) -> Responder | None:
        return await self.session.scalar(select(Responder).where(Responder.account == account))
