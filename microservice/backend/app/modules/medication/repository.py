import datetime as dt
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medication.models import DrugLicense, Medication, MedicationStatus, SlotKey, TimeSlot


class MedicationRepository:
    """medications、time_slots、drug_licenses 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- 藥品 ----------

    async def lock_elder(self, elder_id: UUID) -> None:
        """交易結束前鎖住這位長輩的藥品編號，避免同時新增時拿到同一個編號。"""
        await self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": str(elder_id)})

    async def add(self, medication: Medication) -> Medication:
        self.session.add(medication)
        await self.session.flush()
        await self.session.refresh(medication)
        return medication

    async def get(self, elder_id: UUID, medication_id: UUID) -> Medication | None:
        stmt = select(Medication).where(Medication.id == medication_id, Medication.elder_id == elder_id)
        return await self.session.scalar(stmt)

    async def list_by_elder(self, elder_id: UUID, *, include_stopped: bool = False) -> list[Medication]:
        stmt = select(Medication).where(Medication.elder_id == elder_id)
        if not include_stopped:
            stmt = stmt.where(Medication.status == MedicationStatus.ACTIVE)
        stmt = stmt.order_by(Medication.status, Medication.number, Medication.created_at)
        return list(await self.session.scalars(stmt))

    async def list_all_active(self) -> list[Medication]:
        """所有長輩進行中的藥（排程用）。"""
        stmt = select(Medication).where(Medication.status == MedicationStatus.ACTIVE).order_by(
            Medication.elder_id, Medication.number
        )
        return list(await self.session.scalars(stmt))

    async def latest(self, elder_id: UUID) -> Medication | None:
        """最近一次就醫開的藥（含已停用）。"""
        stmt = (
            select(Medication)
            .where(Medication.elder_id == elder_id)
            .order_by(Medication.start_date.desc(), Medication.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    # ---------- 時段 ----------

    async def ensure_time_slots(self, elder_id: UUID, defaults: dict[SlotKey, dt.time]) -> None:
        """補上還沒建立的時段（已存在的不動）。"""
        stmt = (
            insert(TimeSlot)
            .values([{"elder_id": elder_id, "slot_key": key, "time": t} for key, t in defaults.items()])
            .on_conflict_do_nothing(index_elements=["elder_id", "slot_key"])
        )
        await self.session.execute(stmt)

    async def list_time_slots(self, elder_id: UUID) -> list[TimeSlot]:
        stmt = select(TimeSlot).where(TimeSlot.elder_id == elder_id)
        return list(await self.session.scalars(stmt))

    # ---------- 食藥署資料 ----------

    async def ingredients_by_license(self, license_nos: list[str]) -> dict[str, list[str]]:
        if not license_nos:
            return {}
        stmt = select(DrugLicense.license_no, DrugLicense.ingredients).where(
            DrugLicense.license_no.in_(license_nos)
        )
        rows = await self.session.execute(stmt)
        return {license_no: list(ingredients) for license_no, ingredients in rows}

    async def zh_names_by_license(self, license_nos: list[str]) -> dict[str, str]:
        """許可證字號 → 中文品名（朗讀藥名用）。"""
        if not license_nos:
            return {}
        stmt = select(DrugLicense.license_no, DrugLicense.name_zh).where(DrugLicense.license_no.in_(license_nos))
        rows = await self.session.execute(stmt)
        return {license_no: name_zh for license_no, name_zh in rows}
