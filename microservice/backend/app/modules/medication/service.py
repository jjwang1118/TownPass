import datetime as dt
import json
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.modules.family.service import Access, FamilyService
from app.modules.medication import rules
from app.modules.medication.models import Medication, MedicationSource, MedicationStatus, SlotKey, StopReason
from app.modules.medication.repository import MedicationRepository
from app.modules.medication.schemas import (
    DoseItem,
    LastVisit,
    MedicationCreate,
    MedicationCreated,
    MedicationDraft,
    MedicationOut,
    MedicationUpdate,
    MedicationWarning,
    NextDoseOut,
    QrPreviewOut,
    RxQrPayload,
    TimeSlotItem,
    TimeSlotsUpdate,
    WarningType,
)
from app.modules.speech import rules as speech

# 往後找「下一次吃藥」最多找幾天
_NEXT_DOSE_LOOKAHEAD_DAYS = 7


class MedicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicationRepository(session)
        self.family = FamilyService(session)

    # ---------- 藥品 ----------

    async def list_medications(
        self, user_id: UUID, elder_id: UUID, *, include_stopped: bool = False
    ) -> list[MedicationOut]:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        slot_times = await self.slot_times(elder_id)
        medications = await self.repo.list_by_elder(elder_id, include_stopped=include_stopped)
        zh_names = await self._zh_names(medications)
        await self.session.commit()
        return [self._to_out(m, slot_times, zh_names) for m in medications]

    async def preview_qr(self, user_id: UUID, elder_id: UUID, raw: str | None) -> QrPreviewOut:
        """解析藥袋 QR 給確認畫面，不寫入藥品。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        draft = self._parse_qr(raw)
        slot_times = await self.slot_times(elder_id)
        warnings = await self._warnings(draft.license_no, await self.repo.list_by_elder(elder_id))
        await self.session.commit()
        return QrPreviewOut(
            draft=draft,
            frequency_label=rules.FREQUENCY_LABELS[draft.frequency],
            meal_timing_label=rules.MEAL_TIMING_LABELS[draft.meal_timing],
            slots=self._slot_items(rules.allocate_slots(draft.frequency, draft.meal_timing), slot_times),
            warnings=warnings,
        )

    async def create(self, user_id: UUID, elder_id: UUID, body: MedicationCreate) -> MedicationCreated:
        """長輩在確認畫面核對後加入。本期只有掃藥袋 QR 一種來源。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        slot_times = await self.slot_times(elder_id)

        await self.repo.lock_elder(elder_id)
        active = await self.repo.list_by_elder(elder_id)
        warnings = await self._warnings(body.license_no, active)
        number = rules.next_number({m.number for m in active})

        medication = await self.repo.add(
            Medication(
                elder_id=elder_id,
                number=number,
                **body.model_dump(),
                source=MedicationSource.QR,
                status=MedicationStatus.ACTIVE,
                created_by=user_id,
            )
        )
        zh_names = await self._zh_names([medication])
        await self.session.commit()
        return MedicationCreated(
            medication=self._to_out(medication, slot_times, zh_names),
            warnings=warnings,
            message=f"請在藥袋上寫上大大的 {number}",
        )

    async def get(self, user_id: UUID, elder_id: UUID, medication_id: UUID) -> MedicationOut:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        medication = await self._get(elder_id, medication_id)
        slot_times = await self.slot_times(elder_id)
        zh_names = await self._zh_names([medication])
        await self.session.commit()
        return self._to_out(medication, slot_times, zh_names)

    async def update(
        self, user_id: UUID, elder_id: UUID, medication_id: UUID, body: MedicationUpdate
    ) -> MedicationOut:
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        medication = await self._get(elder_id, medication_id)
        if medication.status is MedicationStatus.STOPPED:
            raise Conflict("這個藥已經停用，不能修改", code="MEDICATION_STOPPED")
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(medication, field, value)
        slot_times = await self.slot_times(elder_id)
        zh_names = await self._zh_names([medication])
        await self.session.commit()
        return self._to_out(medication, slot_times, zh_names)

    async def stop(self, user_id: UUID, elder_id: UUID, medication_id: UUID, reason: StopReason) -> MedicationOut:
        """停用後不再提醒，編號釋放。重複停用不會出錯。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        medication = await self._get(elder_id, medication_id)
        if medication.status is MedicationStatus.ACTIVE:
            medication.status = MedicationStatus.STOPPED
            medication.stopped_at = clock.now()
            medication.stop_reason = reason
        slot_times = await self.slot_times(elder_id)
        zh_names = await self._zh_names([medication])
        await self.session.commit()
        return self._to_out(medication, slot_times, zh_names)

    # ---------- 時段 ----------

    async def list_time_slots(self, user_id: UUID, elder_id: UUID) -> list[TimeSlotItem]:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        slot_times = await self.slot_times(elder_id)
        await self.session.commit()
        return self._slot_items(list(SlotKey), slot_times)

    async def update_time_slots(self, user_id: UUID, elder_id: UUID, body: TimeSlotsUpdate) -> list[TimeSlotItem]:
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        keys = [item.slot_key for item in body.slots]
        if len(keys) != len(set(keys)):
            raise ValidationFailed("同一個時段只能設定一次", code="DUPLICATE_SLOT")

        await self.repo.ensure_time_slots(elder_id, rules.DEFAULT_SLOT_TIMES)
        rows = {row.slot_key: row for row in await self.repo.list_time_slots(elder_id)}
        for item in body.slots:
            rows[item.slot_key].time = item.time
        await self.session.commit()
        return self._slot_items(list(SlotKey), {key: row.time for key, row in rows.items()})

    async def next_dose(self, user_id: UUID, elder_id: UUID) -> NextDoseOut | None:
        """首頁狀態列「下一次吃藥：今天 12:00」。沒有要吃的藥時回傳 null。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        slot_times = await self.slot_times(elder_id)
        active = await self.repo.list_by_elder(elder_id)
        await self.session.commit()

        now = clock.now().astimezone(clock.TAIPEI)
        ordered = sorted(slot_times.items(), key=lambda kv: kv[1])
        for offset in range(_NEXT_DOSE_LOOKAHEAD_DAYS + 1):
            day = now.date() + dt.timedelta(days=offset)
            for slot_key, slot_time in ordered:
                at = dt.datetime.combine(day, slot_time, tzinfo=clock.TAIPEI)
                if at <= now:
                    continue
                items = self._doses(active, slot_key, day)
                if items:
                    return NextDoseOut(
                        slot_key=slot_key,
                        label=rules.SLOT_LABELS[slot_key],
                        at=at,
                        is_today=offset == 0,
                        items=items,
                    )
        return None

    # ---------- 提供給其他模組（呼叫端自行檢查權限） ----------

    async def slot_times(self, elder_id: UUID) -> dict[SlotKey, dt.time]:
        """這位長輩的 7 個時段；第一次使用時建立預設值（由呼叫端 commit）。"""
        await self.repo.ensure_time_slots(elder_id, rules.DEFAULT_SLOT_TIMES)
        return {row.slot_key: row.time for row in await self.repo.list_time_slots(elder_id)}

    async def list_active_doses(self, elder_id: UUID, day: dt.date | None = None) -> list[DoseItem]:
        """正在吃的藥（救命卡用）：進行中、且這天在用藥期間內。"""
        day = day or clock.today_taipei()
        return [
            DoseItem(number=m.number, name=m.name, qty=m.dose_qty)
            for m in await self.repo.list_by_elder(elder_id)
            if rules.is_scheduled_on(m.start_date, m.days, day)
        ]

    async def speech_names(self, elder_id: UUID) -> dict[int, str]:
        """進行中藥品的編號 → 要念的藥名（提醒朗讀用）。"""
        active = await self.repo.list_by_elder(elder_id)
        zh_names = await self._zh_names(active)
        return {m.number: self._drug_name(m, zh_names) for m in active}

    async def doses_for_slot(self, elder_id: UUID, slot_key: SlotKey, day: dt.date) -> list[DoseItem]:
        """某天某時段要吃的藥（提醒用）。"""
        return self._doses(await self.repo.list_by_elder(elder_id), slot_key, day)

    async def elders_scheduled_on(self, day: dt.date) -> list[UUID]:
        """這天有藥要吃的長輩（排程用）。"""
        elder_ids = {
            m.elder_id for m in await self.repo.list_all_active() if rules.is_scheduled_on(m.start_date, m.days, day)
        }
        return sorted(elder_ids)

    async def running_out_on(self, run_out: dt.date) -> dict[UUID, list[int]]:
        """在這天吃完的進行中藥品，依長輩分組回傳編號（回診提醒用）。"""
        result: dict[UUID, list[int]] = {}
        for m in await self.repo.list_all_active():
            if rules.run_out_date(m.start_date, m.days) == run_out:
                result.setdefault(m.elder_id, []).append(m.number)
        return result

    async def soonest_run_out(self, elder_id: UUID) -> list[int]:
        """最快吃完的那幾號藥（Demo 回診提醒用）。"""
        active = await self.repo.list_by_elder(elder_id)
        if not active:
            return []
        soonest = min(rules.run_out_date(m.start_date, m.days) for m in active)
        return [m.number for m in active if rules.run_out_date(m.start_date, m.days) == soonest]

    async def last_visit(self, elder_id: UUID) -> LastVisit | None:
        """最近一次開藥的院區、科別、醫師（回診預約帶入）。"""
        medication = await self.repo.latest(elder_id)
        if medication is None:
            return None
        return LastVisit(
            hospital=medication.hospital,
            department=medication.department,
            doctor=medication.doctor,
            date=medication.start_date,
        )

    # ---------- 內部 ----------

    @staticmethod
    def _parse_qr(raw: str | None) -> MedicationDraft:
        if raw is None:
            raise ValidationFailed("沒有掃到 QR Code", code="QR_EMPTY")
        try:
            payload = RxQrPayload.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise ValidationFailed("這不是藥袋上的 QR Code", code="QR_INVALID") from exc
        return MedicationDraft(
            name=payload.name,
            license_no=payload.lic,
            purpose=payload.use,
            dose_qty=payload.qty,
            frequency=payload.freq,
            meal_timing=payload.meal,
            start_date=payload.date,
            days=payload.days,
            hospital=payload.hosp,
            department=payload.dept,
            doctor=payload.dr,
        )

    async def _warnings(self, license_no: str | None, active: list[Medication]) -> list[MedicationWarning]:
        """和進行中的藥成分相同時標示。只標示，不阻擋。"""
        if not license_no:
            return []
        licenses = [license_no] + [m.license_no for m in active if m.license_no]
        ingredients = await self.repo.ingredients_by_license(licenses)
        return [
            MedicationWarning(
                type=WarningType.SAME_INGREDIENT,
                with_number=m.number,
                message=rules.SAME_INGREDIENT_MESSAGE,
            )
            for m in active
            if rules.same_ingredient(
                license_no, ingredients.get(license_no, []), m.license_no, ingredients.get(m.license_no or "", [])
            )
        ]

    async def _get(self, elder_id: UUID, medication_id: UUID) -> Medication:
        medication = await self.repo.get(elder_id, medication_id)
        if medication is None:
            raise NotFound("找不到這個藥", code="MEDICATION_NOT_FOUND")
        return medication

    @staticmethod
    def _doses(active: list[Medication], slot_key: SlotKey, day: dt.date) -> list[DoseItem]:
        return [
            DoseItem(number=m.number, name=m.name, qty=m.dose_qty)
            for m in sorted(active, key=lambda m: m.number)
            if slot_key in rules.allocate_slots(m.frequency, m.meal_timing)
            and rules.is_scheduled_on(m.start_date, m.days, day)
        ]

    @staticmethod
    def _slot_items(keys: list[SlotKey], slot_times: dict[SlotKey, dt.time]) -> list[TimeSlotItem]:
        return [TimeSlotItem(slot_key=k, label=rules.SLOT_LABELS[k], time=slot_times[k]) for k in keys]

    async def _zh_names(self, medications: list[Medication]) -> dict[str, str]:
        """許可證字號 → 食藥署中文品名，朗讀藥名用。"""
        return await self.repo.zh_names_by_license(sorted({m.license_no for m in medications if m.license_no}))

    @staticmethod
    def _drug_name(m: Medication, zh_names: dict[str, str]) -> str:
        return speech.drug_name(m.name, zh_names.get(m.license_no or ""))

    def _to_out(self, m: Medication, slot_times: dict[SlotKey, dt.time], zh_names: dict[str, str]) -> MedicationOut:
        slots = self._slot_items(rules.allocate_slots(m.frequency, m.meal_timing), slot_times)
        days_left = rules.days_left(m.start_date, m.days, clock.today_taipei())
        return MedicationOut(
            **{field: getattr(m, field) for field in MedicationDraft.model_fields},
            id=m.id,
            number=m.number,
            frequency_label=rules.FREQUENCY_LABELS[m.frequency],
            meal_timing_label=rules.MEAL_TIMING_LABELS[m.meal_timing],
            slots=slots,
            run_out_date=rules.run_out_date(m.start_date, m.days),
            days_left=days_left,
            status=m.status,
            stop_reason=m.stop_reason,
            speech_text=speech.medication_card(
                number=m.number,
                drug=self._drug_name(m, zh_names),
                department=m.department,
                purpose=m.purpose,
                dose_qty=m.dose_qty,
                meal_label=rules.MEAL_TIMING_LABELS[m.meal_timing],
                times=[s.time for s in slots],
                days_left=days_left,
            ),
        )
