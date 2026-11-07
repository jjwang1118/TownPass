import datetime as dt
from uuid import UUID

from sqlalchemy import exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.family.models import FamilyBinding, FamilyInvite


class FamilyRepository:
    """family_invites、family_bindings 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- 邀請碼 ----------

    async def add_invite(self, invite: FamilyInvite) -> FamilyInvite:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def active_code_exists(self, code: str, now: dt.datetime) -> bool:
        stmt = select(
            exists().where(
                FamilyInvite.code == code,
                FamilyInvite.used_at.is_(None),
                FamilyInvite.expires_at > now,
            )
        )
        return bool(await self.session.scalar(stmt))

    async def expire_active_invites(self, elder_id: UUID, now: dt.datetime) -> None:
        await self.session.execute(
            update(FamilyInvite)
            .where(
                FamilyInvite.elder_id == elder_id,
                FamilyInvite.used_at.is_(None),
                FamilyInvite.expires_at > now,
            )
            .values(expires_at=now)
        )

    async def consume_invite(self, code: str, family_id: UUID, now: dt.datetime) -> UUID | None:
        """有效的邀請碼標記為已使用，回傳長輩 id。用一條 UPDATE 確保只能用一次。"""
        result = await self.session.execute(
            update(FamilyInvite)
            .where(
                FamilyInvite.code == code,
                FamilyInvite.used_at.is_(None),
                FamilyInvite.expires_at > now,
            )
            .values(used_at=now, used_by=family_id)
            .returning(FamilyInvite.elder_id)
        )
        return result.scalar_one_or_none()

    async def latest_invite(self, code: str) -> FamilyInvite | None:
        stmt = (
            select(FamilyInvite)
            .where(FamilyInvite.code == code)
            .order_by(FamilyInvite.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    # ---------- 綁定 ----------

    async def add_binding(self, binding: FamilyBinding) -> FamilyBinding:
        self.session.add(binding)
        await self.session.flush()
        await self.session.refresh(binding)
        return binding

    async def get_active_binding(self, binding_id: UUID) -> FamilyBinding | None:
        stmt = select(FamilyBinding).where(FamilyBinding.id == binding_id, FamilyBinding.revoked_at.is_(None))
        return await self.session.scalar(stmt)

    async def find_active_binding(self, elder_id: UUID, family_id: UUID) -> FamilyBinding | None:
        stmt = select(FamilyBinding).where(
            FamilyBinding.elder_id == elder_id,
            FamilyBinding.family_id == family_id,
            FamilyBinding.revoked_at.is_(None),
        )
        return await self.session.scalar(stmt)

    async def list_active_bindings(self, user_id: UUID) -> list[FamilyBinding]:
        stmt = (
            select(FamilyBinding)
            .where(
                or_(FamilyBinding.elder_id == user_id, FamilyBinding.family_id == user_id),
                FamilyBinding.revoked_at.is_(None),
            )
            .order_by(FamilyBinding.created_at)
        )
        return list(await self.session.scalars(stmt))

    async def list_active_bindings_of_elder(self, elder_id: UUID) -> list[FamilyBinding]:
        stmt = (
            select(FamilyBinding)
            .where(FamilyBinding.elder_id == elder_id, FamilyBinding.revoked_at.is_(None))
            .order_by(FamilyBinding.created_at)
        )
        return list(await self.session.scalars(stmt))
