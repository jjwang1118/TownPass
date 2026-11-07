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
from app.modules.auth.service import AuthService
from app.modules.emergency_card import rules
from app.modules.emergency_card.models import (
    AccessMethod,
    CardAccessLog,
    CardCode,
    Consent,
    ConsentType,
    EmergencyCard,
    EmergencyContact,
    Gender,
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
    staff_no: str  # 人員編號


class EmergencyCardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmergencyCardRepository(session)
        self.auth = AuthService(session)
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
            card.special = None
            card.updated_by = user_id
            await self.repo.revoke_codes(card.id, now)
        await self.session.commit()

    # ---------- 救命卡 ----------

    async def get_card(self, user_id: UUID, elder_id: UUID) -> CardOut:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        return await self._card_out(await self._get_card(elder_id))

    async def update_card(self, user_id: UUID, elder_id: UUID, body: CardUpdate) -> CardOut:
        """儲存整張卡（含一位緊急聯絡人）。第一次儲存時建立救命卡並產生卡號。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        await self._require_consent(elder_id)

        values = {
            "name": body.name,
            "birth_date": body.birth_date,
            "gender": body.gender,
            "blood_type": body.blood_type,
            "chronic_conditions": body.chronic_conditions,
            "allergies": [a.model_dump(mode="json") for a in body.allergies],
            "special": body.special,
            "language": body.language,
            "updated_by": user_id,
        }
        card = await self.repo.get_card(elder_id)
        if card is None:
            card = EmergencyCard(elder_id=elder_id, **values)
            await self.repo.add(card)
        else:
            for field, value in values.items():
                setattr(card, field, value)
        contact = body.contact
        await self.repo.replace_contacts(
            card.id,
            [EmergencyContact(card_id=card.id, name=contact.name, relation=contact.relation, phone=contact.phone, sort_order=0)],
        )
        # 新建，或撤回同意後重新同意時，補發卡號
        if await self.repo.active_code(card.id) is None:
            await self._issue_code(card.id)

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
                responder_staff_no=responder.staff_no,
                code_used=code,
                method=method,
                latitude=latitude,
                longitude=longitude,
                accessed_at=now,
            )
        )
        result = ResponderCardOut(
            name=card.name,
            age=rules.age(card.birth_date, clock.today_taipei()),
            gender=card.gender,
            blood_type=card.blood_type,
            contact=await self._contact_out(card.id),
            chronic_conditions=card.chronic_conditions or [],
            allergies=[Allergy.model_validate(a) for a in card.allergies or []],
            special=card.special or [],
            language=card.language,
            current_medications=await self.medication.list_active_doses(card.elder_id),
            close_at=now + RESULT_TTL,
        )
        # 先確保紀錄寫入，再通知家人
        await self.session.commit()
        await self._notify_family(card.elder_id, card.name, responder, now)
        return result

    # ---------- 提供給其他模組（呼叫端自行檢查權限） ----------

    async def elder_profile(self, elder_id: UUID) -> tuple[str, Gender | None] | None:
        """救命卡上的姓名與性別（推播給家屬用）；還沒建立救命卡時回傳 None。"""
        card = await self.repo.get_card(elder_id)
        return (card.name, card.gender) if card else None

    # ---------- 內部 ----------

    async def _notify_family(self, elder_id: UUID, elder_name: str, responder: ResponderInfo, at: dt.datetime) -> None:
        """UI F07：「救護人員查看了王美玉的緊急醫療卡」，附時間、單位、人員編號與撥給長輩的 phone_call 訊息。"""
        local = at.astimezone(clock.TAIPEI)
        call = PhoneCallMessage.to(await self.auth.get_phone(elder_id))
        family_ids = await self.family.list_family_ids(elder_id)
        if not family_ids:
            return
        try:
            await self.notification.push(
                family_ids,
                PushType.CARD_ACCESSED,
                title=f"救護人員查看了{elder_name}的緊急醫療卡",
                body=(
                    f"{local:%m/%d %H:%M}｜臺北市政府消防局 {responder.unit}｜人員編號 {responder.staff_no}。"
                    "長輩可能需要緊急協助，請盡快聯絡。"
                ),
                data={
                    "elder_id": str(elder_id),
                    "accessed_at": local.isoformat(),
                    "unit": f"臺北市政府消防局 {responder.unit}",
                    "staff_no": responder.staff_no,
                    "call": call.model_dump_json(),
                },
            )
        except Exception:  # 推播失敗不影響救護人員查看
            logger.exception("救命卡查看通知發送失敗 elder_id=%s", elder_id)

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

    async def _contact_out(self, card_id: UUID) -> ContactOut | None:
        contacts = await self.repo.list_contacts(card_id)
        if not contacts:
            return None
        c = contacts[0]
        return ContactOut(name=c.name, relation=c.relation, phone=c.phone, call=PhoneCallMessage.to(c.phone))

    async def _card_out(self, card: EmergencyCard) -> CardOut:
        code = await self.repo.active_code(card.id)
        return CardOut(
            name=card.name,
            birth_date=card.birth_date,
            age=rules.age(card.birth_date, clock.today_taipei()),
            gender=card.gender,
            blood_type=card.blood_type,
            contact=await self._contact_out(card.id),
            chronic_conditions=card.chronic_conditions or [],
            allergies=[Allergy.model_validate(a) for a in card.allergies or []],
            special=card.special or [],
            language=card.language,
            current_medications=await self.medication.list_active_doses(card.elder_id),
            code=self._code_out(code) if code else None,
            has_consent=await self.repo.active_consent(card.elder_id, ConsentType.HEALTH_DATA) is not None,
            access_logs=[
                AccessLogOut(
                    responder_name=log.responder_name,
                    responder_unit=log.responder_unit,
                    responder_staff_no=log.responder_staff_no,
                    method=log.method,
                    latitude=log.latitude,
                    longitude=log.longitude,
                    accessed_at=log.accessed_at,
                )
                for log in await self.repo.list_access_logs(card.id)
            ],
            updated_at=card.updated_at,
        )
