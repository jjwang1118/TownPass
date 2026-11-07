import datetime as dt
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.emergency_card.models import (
    CardAccessLog,
    CardCode,
    Consent,
    ConsentType,
    EmergencyCard,
    EmergencyContact,
)

_ACCESS_LOG_LIMIT = 50


class EmergencyCardRepository:
    """emergency_cards、emergency_contacts、card_codes、card_access_logs、consents 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- 救命卡 ----------

    async def get_card(self, elder_id: UUID) -> EmergencyCard | None:
        return await self.session.scalar(select(EmergencyCard).where(EmergencyCard.elder_id == elder_id))

    async def get_card_by_id(self, card_id: UUID) -> EmergencyCard | None:
        return await self.session.get(EmergencyCard, card_id)

    async def add(self, obj: object) -> None:
        self.session.add(obj)
        await self.session.flush()

    async def refresh(self, obj: object) -> None:
        await self.session.refresh(obj)

    # ---------- 緊急聯絡人 ----------

    async def list_contacts(self, card_id: UUID) -> list[EmergencyContact]:
        stmt = select(EmergencyContact).where(EmergencyContact.card_id == card_id).order_by(EmergencyContact.sort_order)
        return list(await self.session.scalars(stmt))

    async def replace_contacts(self, card_id: UUID, contacts: list[EmergencyContact]) -> None:
        await self.session.execute(delete(EmergencyContact).where(EmergencyContact.card_id == card_id))
        self.session.add_all(contacts)
        await self.session.flush()

    # ---------- 卡號 ----------

    async def active_code(self, card_id: UUID) -> CardCode | None:
        stmt = select(CardCode).where(CardCode.card_id == card_id, CardCode.revoked_at.is_(None))
        return await self.session.scalar(stmt)

    async def code_exists(self, code: str) -> bool:
        return await self.session.get(CardCode, code) is not None

    async def find_active_code(self, code: str) -> CardCode | None:
        stmt = select(CardCode).where(CardCode.code == code, CardCode.revoked_at.is_(None))
        return await self.session.scalar(stmt)

    async def revoke_codes(self, card_id: UUID, now: dt.datetime) -> None:
        await self.session.execute(
            update(CardCode).where(CardCode.card_id == card_id, CardCode.revoked_at.is_(None)).values(revoked_at=now)
        )

    # ---------- 查看紀錄 ----------

    async def list_access_logs(self, card_id: UUID) -> list[CardAccessLog]:
        stmt = (
            select(CardAccessLog)
            .where(CardAccessLog.card_id == card_id)
            .order_by(CardAccessLog.accessed_at.desc())
            .limit(_ACCESS_LOG_LIMIT)
        )
        return list(await self.session.scalars(stmt))

    # ---------- 同意 ----------

    async def active_consent(self, user_id: UUID, type: ConsentType) -> Consent | None:
        stmt = select(Consent).where(Consent.user_id == user_id, Consent.type == type, Consent.revoked_at.is_(None))
        return await self.session.scalar(stmt)
