from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def list_by_ids(self, user_ids: list[UUID]) -> list[User]:
        if not user_ids:
            return []
        return list(await self.session.scalars(select(User).where(User.id.in_(user_ids))))

    async def get_by_townpass_id(self, townpass_id: str) -> User | None:
        result = await self.session.execute(select(User).where(User.townpass_id == townpass_id))
        return result.scalar_one_or_none()

    async def list_by_id_no_hash(self, id_no_hash: str) -> list[User]:
        stmt = select(User).where(User.id_no_hash == id_no_hash).order_by(User.created_at.desc())
        return list(await self.session.scalars(stmt))

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
