import datetime as dt
import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, NotFound
from app.integrations.townpass.messages import PhoneCallMessage
from app.modules.emergency_card import rules
from app.modules.emergency_card.models import (
    AccessMethod,
    CardAccessLog,
    CardCode,
    Consent,
    ConsentType,
    EmergencyCard,
    EmergencyContact,
)
from app.modules.emergency_card.repository import EmergencyCardRepository
from app.modules.emergency_card.schemas import (
    AccessLogOut,
    Allergy,
    CardCodeOut,
    CardOut,
    CardUpdate,
    CommonItemsOut,
    ConsentOut,
    ContactOut,
    ContactsUpdate,
    ResponderCardOut,
)
from app.modules.family.service import Access, FamilyService
from app.modules.medication.service import MedicationService
from app.modules.notification.schemas import PushType
from app.modules.notification.service import NotificationService

logger = logging.getLogger(__name__)

# 救護人員查詢結果多久後自動關閉（交付規格：30 分鐘）
RESULT_TTL = dt.timedelta(minutes=30)
_MAX_CODE_ATTEMPTS = 10


@dataclass(frozen=True)
class ResponderInfo:
    """responder 模組傳進來的救護人員資料（救命卡模組不 import responder，避免循環依賴）。"""

    id: UUID
    name: str
    unit: str
    unit_phone: str


class EmergencyCardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmergencyCardRepository(session)
        self.family = FamilyService(session)
        self.medication = MedicationService(session)
        self.notification = NotificationService(session)

    @staticmethod
    def common_items() -> CommonItemsOut:
        return CommonItemsOut(
            chronic_conditions=rules.COMMON_CHRONIC_CONDITIONS,
            allergies=[Allergy.model_validate(a) for a in rules.COMMON_ALLERGIES],
        )

    # ---------- 同意（個資法第 6 條） ----------

    async def grant_consent(self, user_id: UUID, elder_id: UUID, type: ConsentType) -> ConsentOut:
        """長輩本人或初始設定中的家人協助勾選。已同意時直接回傳原本的紀錄。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        consent = await self.repo.active_consent(elder_id, type)
        if consent is None:
            consent = Consent(user_id=elder_id, type=type, granted_at=clock.now(), granted_by=user_id)
            await self.repo.add(consent)
        await self.session.commit()
        return ConsentOut(type=consent.type, granted_at=consent.granted_at)

    async def revoke_consent(self, user_id: UUID, elder_id: UUID, type: ConsentType) -> None:
        """只有長輩本人可以撤回。清空慢性病、過敏，卡號立即失效；查看紀錄保留。"""
        if user_id != elder_id:
            raise Forbidden("只有長輩本人可以撤回同意", code="ELDER_ONLY")
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)

        consent = await self.repo.active_consent(elder_id, type)
        if consent is None:
            return
        now = clock.now()
        consent.revoked_at = now
        card = await self.repo.get_card(elder_id)
        if card is not None:
            card.chronic_conditions = None
            card.allergies = None
            card.updated_by = user_id
            await self.repo.revoke_codes(card.id, now)
        await self.session.commit()

    # ---------- 救命卡 ----------

    async def get_card(self, user_id: UUID, elder_id: UUID) -> CardOut:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        return await self._card_out(await self._get_card(elder_id))

    async def update_card(self, user_id: UUID, elder_id: UUID, body: CardUpdate) -> CardOut:
        """第一次儲存時建立救命卡並產生卡號。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        await self._require_consent(elder_id)

        values = {
            "title": body.title,
            "birth_year": body.birth_year,
            "gender": body.gender,
            "chronic_conditions": body.chronic_conditions,
            "allergies": [a.model_dump(mode="json") for a in body.allergies],
            "hospital": body.hospital,
            "updated_by": user_id,
        }
        card = await self.repo.get_card(elder_id)
        if card is None:
            card = EmergencyCard(elder_id=elder_id, **values)
            await self.repo.add(card)
        else:
            for field, value in values.items():
                setattr(card, field, value)
        # 新建，或撤回同意後重新同意時，補發卡號
        if await self.repo.active_code(card.id) is None:
            await self._issue_code(card.id)

        await self.session.commit()
        await self.repo.refresh(card)
        return await self._card_out(card)

    async def update_contacts(self, user_id: UUID, elder_id: UUID, body: ContactsUpdate) -> CardOut:
        """整批取代緊急聯絡人（最多 2 位）。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        card = await self._get_card(elder_id)
        await self.repo.replace_contacts(
            card.id,
            [
                EmergencyContact(card_id=card.id, name=c.name, relation=c.relation, phone=c.phone, sort_order=i)
                for i, c in enumerate(body.contacts)
            ],
        )
        card.updated_by = user_id
        await self.session.commit()
        await self.repo.refresh(card)
        return await self._card_out(card)

    async def regenerate_code(self, user_id: UUID, elder_id: UUID) -> CardCodeOut:
        """卡片遺失或外流時，長輩或任何綁定的家人都可以重新產生（功能規格 2-3）；舊卡號立即失效。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        card = await self._get_card(elder_id)
        await self._require_consent(elder_id)
        await self.repo.revoke_codes(card.id, clock.now())
        code = await self._issue_code(card.id)
        await self.session.commit()
        return self._code_out(code)

    # ---------- 救護人員查詢（由 responder 模組呼叫） ----------

    async def lookup_for_responder(
        self,
        responder: ResponderInfo,
        code: str,
        method: AccessMethod,
        latitude: Decimal | None,
        longitude: Decimal | None,
    ) -> ResponderCardOut:
        """顯示救命卡、留查看紀錄、通知所有綁定的家人。"""
        card_code = await self.repo.find_active_code(code)
        if card_code is None:
            raise NotFound("查無此救命卡，請確認卡號", code="CARD_NOT_FOUND")
        card = await self.repo.get_card_by_id(card_code.card_id)
        assert card is not None

        now = clock.now()
        await self.repo.add(
            CardAccessLog(
                card_id=card.id,
                responder_id=responder.id,
                responder_name=responder.name,
                responder_unit=responder.unit,
                code_used=code,
                method=method,
                latitude=latitude,
                longitude=longitude,
                accessed_at=now,
            )
        )
        result = ResponderCardOut(
            title=card.title,
            birth_year=card.birth_year,
            gender=card.gender,
            allergies=[Allergy.model_validate(a) for a in card.allergies or []],
            current_medications=await self.medication.list_active_doses(card.elder_id),
            chronic_conditions=card.chronic_conditions or [],
            contacts=await self._contacts_out(card.id),
            hospital=card.hospital,
            close_at=now + RESULT_TTL,
        )
        # 先確保紀錄寫入，再通知家人
        await self.session.commit()
        await self._notify_family(card.elder_id, responder, now)
        return result

    # ---------- 內部 ----------

    async def _notify_family(self, elder_id: UUID, responder: ResponderInfo, at: dt.datetime) -> None:
        """「臺北市消防局中山分隊王大明於 15:20 查看了媽媽的救命卡」，附撥給分隊的 phone_call 訊息。"""
        time_text = at.astimezone(clock.TAIPEI).strftime("%H:%M")
        call = PhoneCallMessage.to(responder.unit_phone)
        for member in await self.family.list_family_members(elder_id):
            try:
                await self.notification.push(
                    [member.family_id],
                    PushType.CARD_ACCESSED,
                    title="救命卡查看通知",
                    body=f"臺北市消防局{responder.unit}{responder.name}於 {time_text} 查看了{member.relation_label}的救命卡",
                    data={"elder_id": str(elder_id), "call": call.model_dump_json()},
                )
            except Exception:  # 推播失敗不影響救護人員查看
                logger.exception("救命卡查看通知發送失敗 family_id=%s", member.family_id)

    async def _get_card(self, elder_id: UUID) -> EmergencyCard:
        card = await self.repo.get_card(elder_id)
        if card is None:
            raise NotFound("還沒有建立救命卡", code="CARD_NOT_CREATED")
        return card

    async def _require_consent(self, elder_id: UUID) -> None:
        if await self.repo.active_consent(elder_id, ConsentType.HEALTH_DATA) is None:
            raise Forbidden("請先勾選同意儲存健康資料", code="CONSENT_REQUIRED")

    async def _issue_code(self, card_id: UUID) -> CardCode:
        for _ in range(_MAX_CODE_ATTEMPTS):
            code = rules.generate_code()
            if not await self.repo.code_exists(code):
                break
        else:  # pragma: no cover - 約 8.5 × 10¹¹ 種組合，幾乎不會連續撞號
            raise Conflict("請稍後再試", code="CARD_CODE_BUSY")
        card_code = CardCode(code=code, card_id=card_id)
        await self.repo.add(card_code)
        return card_code

    @staticmethod
    def _code_out(code: CardCode) -> CardCodeOut:
        return CardCodeOut(code=code.code, qr_url=rules.qr_url(get_settings().frontend_base_url, code.code))

    async def _contacts_out(self, card_id: UUID) -> list[ContactOut]:
        return [
            ContactOut(name=c.name, relation=c.relation, phone=c.phone, call=PhoneCallMessage.to(c.phone))
            for c in await self.repo.list_contacts(card_id)
        ]

    async def _card_out(self, card: EmergencyCard) -> CardOut:
        code = await self.repo.active_code(card.id)
        return CardOut(
            title=card.title,
            birth_year=card.birth_year,
            gender=card.gender,
            current_medications=await self.medication.list_active_doses(card.elder_id),
            chronic_conditions=card.chronic_conditions or [],
            allergies=[Allergy.model_validate(a) for a in card.allergies or []],
            contacts=await self._contacts_out(card.id),
            hospital=card.hospital,
            code=self._code_out(code) if code else None,
            has_consent=await self.repo.active_consent(card.elder_id, ConsentType.HEALTH_DATA) is not None,
            access_logs=[
                AccessLogOut(
                    responder_name=log.responder_name,
                    responder_unit=log.responder_unit,
                    method=log.method,
                    latitude=log.latitude,
                    longitude=log.longitude,
                    accessed_at=log.accessed_at,
                )
                for log in await self.repo.list_access_logs(card.id)
            ],
            updated_at=card.updated_at,
        )
