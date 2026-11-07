import datetime as dt
from uuid import UUID

from sqlalchemy import Select, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medication.models import (
    DrugLicense,
    Medication,
    MedicationStatus,
    Prescription,
    PrescriptionStatus,
)

_SEARCH_CANDIDATES = 400


class MedicationRepository:
    """prescriptions、medications、drug_licenses 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- 藥單 ----------

    async def lock_elder(self, elder_id: UUID) -> None:
        """交易結束前鎖住這位長輩的藥單字母，避免同時新增時拿到同一個字母。"""
        await self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": str(elder_id)})

    async def add(self, obj: object) -> None:
        self.session.add(obj)
        await self.session.flush()

    async def finish_expired(self, elder_id: UUID | None, today: dt.date, now: dt.datetime) -> None:
        """已經過了吃藥天數的藥單改為「已吃完」，釋放字母。elder_id 為 None 時處理所有長輩。"""
        stmt = (
            update(Prescription)
            .where(
                Prescription.status == PrescriptionStatus.ACTIVE,
                Prescription.visit_date + Prescription.days <= today,  # 吃完日的隔天起
            )
            .values(status=PrescriptionStatus.FINISHED, finished_at=now)
        )
        if elder_id is not None:
            stmt = stmt.where(Prescription.elder_id == elder_id)
        await self.session.execute(stmt)

    async def get_prescription(self, elder_id: UUID, prescription_id: UUID) -> Prescription | None:
        stmt = select(Prescription).where(Prescription.id == prescription_id, Prescription.elder_id == elder_id)
        return await self.session.scalar(stmt)

    async def list_prescriptions(self, elder_id: UUID, status: PrescriptionStatus) -> list[Prescription]:
        stmt = select(Prescription).where(Prescription.elder_id == elder_id, Prescription.status == status)
        if status is PrescriptionStatus.ACTIVE:
            stmt = stmt.order_by(Prescription.letter)
        else:
            stmt = stmt.order_by(Prescription.visit_date.desc(), Prescription.created_at.desc())
        return list(await self.session.scalars(stmt))

    async def active_letters(self, elder_id: UUID) -> set[str]:
        stmt = select(Prescription.letter).where(
            Prescription.elder_id == elder_id, Prescription.status == PrescriptionStatus.ACTIVE
        )
        return set(await self.session.scalars(stmt))

    async def latest_active_prescription(self, elder_id: UUID) -> Prescription | None:
        """最近看診的吃藥中藥單（回診預約帶入科別）。"""
        stmt = (
            select(Prescription)
            .where(Prescription.elder_id == elder_id, Prescription.status == PrescriptionStatus.ACTIVE)
            .order_by(Prescription.visit_date.desc(), Prescription.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    # ---------- 藥品 ----------

    def _active_query(self) -> Select[tuple[Medication, Prescription]]:
        return (
            select(Medication, Prescription)
            .join(Prescription, Medication.prescription_id == Prescription.id)
            .where(
                Medication.status == MedicationStatus.ACTIVE,
                Prescription.status == PrescriptionStatus.ACTIVE,
            )
            .order_by(Prescription.letter, Medication.seq)
        )

    async def list_active(self, elder_id: UUID) -> list[tuple[Medication, Prescription]]:
        """吃藥中藥單裡、還沒停用的藥，依編號排序。"""
        rows = await self.session.execute(self._active_query().where(Medication.elder_id == elder_id))
        return [(m, p) for m, p in rows.all()]

    async def list_all_active(self) -> list[tuple[Medication, Prescription]]:
        """所有長輩吃藥中的藥（排程用）。"""
        rows = await self.session.execute(self._active_query())
        return [(m, p) for m, p in rows.all()]

    async def list_by_prescriptions(self, prescription_ids: list[UUID]) -> list[Medication]:
        if not prescription_ids:
            return []
        stmt = (
            select(Medication)
            .where(Medication.prescription_id.in_(prescription_ids))
            .order_by(Medication.prescription_id, Medication.seq)
        )
        return list(await self.session.scalars(stmt))

    async def get_medication(self, elder_id: UUID, medication_id: UUID) -> tuple[Medication, Prescription] | None:
        stmt = (
            select(Medication, Prescription)
            .join(Prescription, Medication.prescription_id == Prescription.id)
            .where(Medication.id == medication_id, Medication.elder_id == elder_id)
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    # ---------- 藥品資料（健保用藥品項） ----------

    async def get_licenses(self, license_nos: list[str]) -> dict[str, DrugLicense]:
        if not license_nos:
            return {}
        stmt = select(DrugLicense).where(DrugLicense.license_no.in_(license_nos))
        return {d.license_no: d for d in await self.session.scalars(stmt)}

    async def ingredients_by_license(self, license_nos: list[str]) -> dict[str, list[str]]:
        return {no: list(d.ingredients) for no, d in (await self.get_licenses(license_nos)).items()}

    async def names_by_license(self, license_nos: list[str]) -> dict[str, tuple[str, str | None]]:
        """藥品代號 →（中文品名, 英文品名），朗讀藥名用。"""
        return {no: (d.name_zh, d.name_en) for no, d in (await self.get_licenses(license_nos)).items()}

    async def search_candidates(self, prefixes: list[str]) -> list[DrugLicense]:
        """藥名搜尋與辨識比對的候選：產品名、主成分、中文名的開頭或其中一個字符合任一個前綴。

        回傳後由 service 依規則精確比對與排序。
        """
        conditions = []
        for prefix in prefixes:
            if not prefix:
                continue
            like, word = f"{prefix}%", f"% {prefix}%"
            conditions += [
                DrugLicense.product_en.ilike(like),
                DrugLicense.product_en.ilike(word),
                DrugLicense.ingredient_en.ilike(like),
                DrugLicense.product_zh.ilike(like),
                DrugLicense.product_zh.ilike(word),
                DrugLicense.name_zh.ilike(f"%{prefix}%") if not prefix.isascii() else DrugLicense.name_en.ilike(like),
            ]
        if not conditions:
            return []
        stmt = select(DrugLicense).where(or_(*conditions)).limit(_SEARCH_CANDIDATES * 5)
        return list(await self.session.scalars(stmt))
