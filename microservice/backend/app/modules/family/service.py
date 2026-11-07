from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.modules.auth.models import UserRole
from app.modules.auth.schemas import MeOut
from app.modules.auth.service import AuthService
from app.modules.family import rules
from app.modules.family.models import FamilyBinding, FamilyInvite
from app.modules.family.repository import FamilyRepository
from app.modules.family.schemas import BindingCreate, BindingOut, BindingUpdate, InviteOut

_MAX_CODE_ATTEMPTS = 10


class Access(StrEnum):
    READ = "read"
    WRITE = "write"  # 長輩本人，或尚未完成初始設定的綁定家人


@dataclass(frozen=True)
class FamilyMember:
    family_id: UUID
    relation_label: str
    notify_on_ack: bool


class FamilyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FamilyRepository(session)
        self.auth = AuthService(session)

    # ---------- 提供給其他模組 ----------

    async def ensure_access(self, user_id: UUID, elder_id: UUID, access: Access) -> None:
        """權限矩陣（規格書 §3.1）。其他模組存取長輩資料前都要呼叫。"""
        if user_id == elder_id:
            await self._require_role(user_id, UserRole.ELDER)
            return

        binding = await self.repo.find_active_binding(elder_id, user_id)
        if binding is None:
            raise Forbidden("沒有綁定這位長輩", code="NOT_BOUND")
        if access is Access.WRITE and binding.setup_completed_at is not None:
            raise Forbidden("家人只能檢視，不能修改", code="READ_ONLY")

    async def list_family_ids(self, elder_id: UUID, *, ack_subscribers_only: bool = False) -> list[UUID]:
        """要通知的家人。ack_subscribers_only=True 時只回傳有開啟「長輩回應通知」的家人。"""
        return [
            m.family_id
            for m in await self.list_family_members(elder_id)
            if m.notify_on_ack or not ack_subscribers_only
        ]

    async def list_family_members(self, elder_id: UUID) -> list[FamilyMember]:
        """綁定的家人與他們對長輩的稱呼（如「媽媽」），用於組通知文字。"""
        return [
            FamilyMember(family_id=b.family_id, relation_label=b.relation_label, notify_on_ack=b.notify_on_ack)
            for b in await self.repo.list_active_bindings_of_elder(elder_id)
        ]

    # ---------- 邀請碼 ----------

    async def create_invite(self, elder_id: UUID) -> InviteOut:
        await self._require_role(elder_id, UserRole.ELDER)
        now = clock.now()

        # 一位長輩同時只有一組有效邀請碼
        await self.repo.expire_active_invites(elder_id, now)

        for _ in range(_MAX_CODE_ATTEMPTS):
            code = rules.generate_invite_code()
            if not await self.repo.active_code_exists(code, now):
                break
        else:  # pragma: no cover - 10 次都撞到有效邀請碼的機率極低
            raise Conflict("請稍後再試", code="INVITE_CODE_BUSY")

        invite = await self.repo.add_invite(
            FamilyInvite(elder_id=elder_id, code=code, expires_at=now + rules.INVITE_TTL)
        )
        await self.session.commit()
        return InviteOut(
            code=invite.code,
            qr_url=rules.invite_qr_url(get_settings().frontend_base_url, invite.code),
            expires_at=invite.expires_at,
        )

    async def accept_invite(self, family_id: UUID, body: BindingCreate) -> BindingOut:
        await self._require_role(family_id, UserRole.FAMILY)
        code = rules.code_from_input(body.raw_code)
        if code is None:
            raise ValidationFailed("邀請碼格式不正確", code="INVITE_INVALID")

        now = clock.now()
        elder_id = await self.repo.consume_invite(code, family_id, now)
        if elder_id is None:
            await self._raise_invite_unusable(code)

        if await self.repo.find_active_binding(elder_id, family_id) is not None:
            # 不 commit，邀請碼保持未使用
            raise Conflict("已經綁定這位長輩", code="ALREADY_BOUND")

        binding = await self.repo.add_binding(
            FamilyBinding(elder_id=elder_id, family_id=family_id, relation_label=body.relation_label)
        )
        await self.session.commit()
        return (await self._to_out([binding]))[0]

    # ---------- 綁定 ----------

    async def list_bindings(self, user_id: UUID) -> list[BindingOut]:
        return await self._to_out(await self.repo.list_active_bindings(user_id))

    async def update_binding(self, user_id: UUID, binding_id: UUID, body: BindingUpdate) -> BindingOut:
        binding = await self._get_binding(binding_id)
        if binding.family_id != user_id:
            raise Forbidden("只有家人本人可以修改")
        if body.notify_on_ack is not None:
            binding.notify_on_ack = body.notify_on_ack
        if body.relation_label is not None:
            binding.relation_label = body.relation_label
        await self.session.commit()
        return (await self._to_out([binding]))[0]

    async def complete_setup(self, family_id: UUID, binding_id: UUID) -> BindingOut:
        binding = await self._get_binding(binding_id)
        if binding.family_id != family_id:
            raise Forbidden("只有家人本人可以完成設定")
        if binding.setup_completed_at is None:
            binding.setup_completed_at = clock.now()
            await self.session.commit()
        return (await self._to_out([binding]))[0]

    async def revoke_binding(self, elder_id: UUID, binding_id: UUID) -> None:
        binding = await self._get_binding(binding_id)
        if binding.elder_id != elder_id:
            raise Forbidden("只有長輩可以解除綁定")
        binding.revoked_at = clock.now()
        await self.session.commit()

    # ---------- 內部 ----------

    async def _require_role(self, user_id: UUID, role: UserRole) -> MeOut:
        me = await self.auth.get_me(user_id)
        if me.role is None:
            raise Forbidden("請先選擇身分", code="ROLE_REQUIRED")
        if me.role is not role:
            label = "長輩" if role is UserRole.ELDER else "家人"
            raise Forbidden(f"這個功能只有{label}可以使用", code=f"{role.value.upper()}_ONLY")
        return me

    async def _raise_invite_unusable(self, code: str) -> NoReturn:
        """邀請碼無法使用時，判斷原因並丟出對應的錯誤。"""
        invite = await self.repo.latest_invite(code)
        if invite is None:
            raise NotFound("找不到這組邀請碼", code="INVITE_NOT_FOUND")
        if invite.used_at is not None:
            raise Conflict("邀請碼已經使用過，請長輩重新產生", code="INVITE_USED")
        raise Conflict("邀請碼已過期，請長輩重新產生", code="INVITE_EXPIRED")

    async def _get_binding(self, binding_id: UUID) -> FamilyBinding:
        binding = await self.repo.get_active_binding(binding_id)
        if binding is None:
            raise NotFound("找不到這筆綁定", code="BINDING_NOT_FOUND")
        return binding

    async def _to_out(self, bindings: list[FamilyBinding]) -> list[BindingOut]:
        names = await self.auth.get_profiles([b.elder_id for b in bindings] + [b.family_id for b in bindings])
        return [
            BindingOut(
                id=b.id,
                elder_id=b.elder_id,
                elder_name=names[b.elder_id].real_name,
                family_id=b.family_id,
                family_name=names[b.family_id].real_name,
                relation_label=b.relation_label,
                notify_on_ack=b.notify_on_ack,
                can_setup=b.setup_completed_at is None,
                created_at=b.created_at,
            )
            for b in bindings
        ]
