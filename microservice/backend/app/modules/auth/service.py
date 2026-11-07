from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Conflict, NotFound
from app.core.security import TokenKind, hash_id_no, issue_token
from app.integrations.townpass.messages import TownPassAccount
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import MeOut, TokenOut


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def login_with_townpass(self, account: TownPassAccount) -> TokenOut:
        """以 App 回傳的 userinfo 建立或更新使用者，發 JWT。

        比賽時直接信任前端轉送的 userinfo；正式版需改為伺服器端驗證（規格書 §13）。
        """
        user = await self.users.get_by_townpass_id(account.id)
        if user is None:
            user = await self.users.add(
                User(
                    townpass_id=account.id,
                    real_name=account.real_name,
                    phone=account.phone_no,
                    birth_year=account.birth_year,
                    id_no_hash=hash_id_no(account.id_no),
                )
            )
        else:
            user.real_name = account.real_name
            user.phone = account.phone_no
            user.birth_year = account.birth_year
            user.id_no_hash = hash_id_no(account.id_no)
        await self.session.commit()

        token, expires_at = issue_token(user.id, TokenKind.USER)
        return TokenOut(access_token=token, expires_at=expires_at, user=self._me(user))

    async def set_role(self, user_id: UUID, role: UserRole) -> MeOut:
        user = await self._get(user_id)
        if user.role is not None and user.role != role and not get_settings().demo_mode:
            raise Conflict("身分已選擇，不能更改", code="ROLE_ALREADY_SET")
        user.role = role
        await self.session.commit()
        return self._me(user)

    async def elder_ids_by_id_no(self, id_no: str) -> list[UUID]:
        """救護人員以身分證字號查詢：比對雜湊，回符合的長輩（新的在前）。"""
        users = await self.users.list_by_id_no_hash(hash_id_no(id_no))
        return [u.id for u in users if u.role is UserRole.ELDER]

    async def get_me(self, user_id: UUID) -> MeOut:
        return self._me(await self._get(user_id))

    async def get_phone(self, user_id: UUID) -> str:
        """台北通登記的電話（加密儲存），給家人一鍵撥號用。"""
        return (await self._get(user_id)).phone

    async def get_profiles(self, user_ids: list[UUID]) -> dict[UUID, MeOut]:
        """給其他模組查詢多位使用者的姓名、身分。"""
        users = await self.users.list_by_ids(list(set(user_ids)))
        return {user.id: self._me(user) for user in users}

    async def _get(self, user_id: UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFound("找不到使用者")
        return user

    @staticmethod
    def _me(user: User) -> MeOut:
        return MeOut(id=user.id, role=user.role, real_name=user.real_name, birth_year=user.birth_year)
