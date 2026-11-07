from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotImplementedYet
from app.modules.medication.repository import MedicationRepository
from app.modules.medication.schemas import (
    DoseItem,
    MedicationCreate,
    MedicationCreated,
    MedicationOut,
    MedicationUpdate,
    NextDoseOut,
    QrPreviewOut,
    TimeSlotItem,
    TimeSlotsUpdate,
)


class MedicationService:
    """寫入前須先呼叫 FamilyService.ensure_access 檢查權限。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicationRepository(session)

    async def list_medications(self, user_id: UUID, elder_id: UUID) -> list[MedicationOut]:
        raise NotImplementedYet()

    async def list_active_doses(self, elder_id: UUID) -> list[DoseItem]:
        """給救命卡模組帶入「正在吃的藥」。"""
        raise NotImplementedYet()

    async def preview_qr(self, user_id: UUID, elder_id: UUID, raw: str | None) -> QrPreviewOut:
        raise NotImplementedYet()

    async def create(self, user_id: UUID, elder_id: UUID, body: MedicationCreate) -> MedicationCreated:
        raise NotImplementedYet()

    async def get(self, user_id: UUID, elder_id: UUID, medication_id: UUID) -> MedicationOut:
        raise NotImplementedYet()

    async def update(
        self, user_id: UUID, elder_id: UUID, medication_id: UUID, body: MedicationUpdate
    ) -> MedicationOut:
        raise NotImplementedYet()

    async def stop(self, user_id: UUID, elder_id: UUID, medication_id: UUID) -> MedicationOut:
        raise NotImplementedYet()

    async def list_time_slots(self, user_id: UUID, elder_id: UUID) -> list[TimeSlotItem]:
        raise NotImplementedYet()

    async def update_time_slots(self, user_id: UUID, elder_id: UUID, body: TimeSlotsUpdate) -> list[TimeSlotItem]:
        raise NotImplementedYet()

    async def next_dose(self, user_id: UUID, elder_id: UUID) -> NextDoseOut | None:
        raise NotImplementedYet()
