from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotImplementedYet
from app.modules.emergency_card.models import AccessMethod, ConsentType
from app.modules.emergency_card.repository import EmergencyCardRepository
from app.modules.emergency_card.rules import COMMON_ALLERGIES, COMMON_CHRONIC_CONDITIONS
from app.modules.emergency_card.schemas import (
    Allergy,
    CardCodeOut,
    CardOut,
    CardUpdate,
    CommonItemsOut,
    ConsentOut,
    ContactsUpdate,
    ResponderCardOut,
)


class EmergencyCardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmergencyCardRepository(session)

    @staticmethod
    def common_items() -> CommonItemsOut:
        return CommonItemsOut(
            chronic_conditions=COMMON_CHRONIC_CONDITIONS,
            allergies=[Allergy.model_validate(a) for a in COMMON_ALLERGIES],
        )

    async def grant_consent(self, user_id: UUID, elder_id: UUID, type: ConsentType) -> ConsentOut:
        raise NotImplementedYet()

    async def revoke_consent(self, user_id: UUID, elder_id: UUID, type: ConsentType) -> None:
        """清空慢性病、過敏，撤銷有效卡號；查看紀錄保留（規格書 §5.4）。"""
        raise NotImplementedYet()

    async def get_card(self, user_id: UUID, elder_id: UUID) -> CardOut:
        raise NotImplementedYet()

    async def update_card(self, user_id: UUID, elder_id: UUID, body: CardUpdate) -> CardOut:
        raise NotImplementedYet()

    async def update_contacts(self, user_id: UUID, elder_id: UUID, body: ContactsUpdate) -> CardOut:
        raise NotImplementedYet()

    async def regenerate_code(self, user_id: UUID, elder_id: UUID) -> CardCodeOut:
        raise NotImplementedYet()

    async def lookup_for_responder(
        self,
        responder_id: UUID,
        code: str,
        method: AccessMethod,
        latitude: Decimal | None,
        longitude: Decimal | None,
    ) -> ResponderCardOut:
        """寫查看紀錄並推播所有綁定家人。由 responder 模組呼叫。"""
        raise NotImplementedYet()
