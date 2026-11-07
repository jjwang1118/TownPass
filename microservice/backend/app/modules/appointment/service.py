import datetime as dt
import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import Conflict, NotFound
from app.integrations.townpass.messages import LaunchMapMessage
from app.modules.appointment import rules
from app.modules.appointment.models import (
    Appointment,
    AppointmentStatus,
    ClinicSession,
    ClinicSlot,
    Hospital,
    SessionStatus,
)
from app.modules.appointment.repository import AppointmentRepository, AppointmentRow
from app.modules.appointment.schemas import (
    AppointmentCreate,
    AppointmentOut,
    ClinicDayOut,
    DepartmentOut,
    DoctorOut,
    HospitalOut,
    SlotOut,
)
from app.modules.auth.service import AuthService
from app.modules.emergency_card.service import EmergencyCardService
from app.modules.family.service import Access, FamilyService
from app.modules.medication.schemas import LastVisit
from app.modules.medication.service import MedicationService
from app.modules.notification.schemas import PushType
from app.modules.notification.service import NotificationService
from app.modules.reminder.rules import pronoun

logger = logging.getLogger(__name__)

BOOKED_MESSAGE = "回診前一天，您和家屬都會收到提醒。"


class AppointmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AppointmentRepository(session)
        self.auth = AuthService(session)
        self.cards = EmergencyCardService(session)
        self.family = FamilyService(session)
        self.medication = MedicationService(session)
        self.notification = NotificationService(session)

    # ---------- 選院區、科別、醫師、日期、時段 ----------

    async def list_hospitals(self) -> list[HospitalOut]:
        return [self._hospital_out(h) for h in await self.repo.list_hospitals()]

    async def list_departments(self, user_id: UUID, hospital_id: UUID, elder_id: UUID | None) -> list[DepartmentOut]:
        """elder_id 有值時，從最近的藥單帶入科別，排第一個（「已從藥單 A 帶入科別」）。"""
        if await self.repo.get_hospital(hospital_id) is None:
            raise NotFound("找不到這個院區", code="HOSPITAL_NOT_FOUND")
        last = await self._last_visit(user_id, elder_id)
        departments = []
        for d in await self.repo.list_departments(hospital_id):
            matched = last is not None and d.name == last.department
            departments.append(
                DepartmentOut(id=d.id, name=d.name, last_visited=matched, from_letter=last.letter if matched else None)  # type: ignore[union-attr]
            )
        return sorted(departments, key=lambda d: not d.last_visited)  # 穩定排序，其餘維持原順序

    async def list_doctors(self, user_id: UUID, department_id: UUID, elder_id: UUID | None) -> list[DoctorOut]:
        """醫師與每週門診時間；2 週內都額滿或停診時不可選。藥單上的醫師排第一並標記。"""
        department = await self.repo.get_department(department_id)
        if department is None:
            raise NotFound("找不到這個科別", code="DEPARTMENT_NOT_FOUND")
        last = await self._last_visit(user_id, elder_id)
        same_department = last is not None and last.department == department.name

        doctors = await self.repo.list_doctors(department_id)
        start, end = rules.booking_window(clock.today_taipei())
        sessions = await self.repo.list_sessions([d.id for d in doctors], start, end)
        open_ids = await self._available_session_ids(sessions)
        result = []
        for d in doctors:
            mine = [s for s in sessions if s.doctor_id == d.id]
            available = any(s.id in open_ids for s in mine)
            result.append(
                DoctorOut(
                    id=d.id,
                    name=d.name,
                    last_visited=same_department and d.name == last.doctor,  # type: ignore[union-attr]
                    schedule=rules.weekly_schedule((s.date, s.period) for s in mine),
                    available=available,
                    note=None if available else "已額滿",
                )
            )
        return sorted(result, key=lambda d: not d.last_visited)

    async def list_clinic_days(self, doctor_id: UUID) -> list[ClinicDayOut]:
        """明天起 2 週這位醫師的門診；停診、每個時間都額滿時不可選。"""
        if await self.repo.get_doctor(doctor_id) is None:
            raise NotFound("找不到這位醫師", code="DOCTOR_NOT_FOUND")
        start, end = rules.booking_window(clock.today_taipei())
        sessions = sorted(
            await self.repo.list_sessions([doctor_id], start, end),
            key=lambda s: (s.date, rules.PERIOD_ORDER[s.period]),
        )
        open_ids = await self._available_session_ids(sessions)
        days = []
        for s in sessions:
            if s.status is SessionStatus.SUSPENDED:
                note = "停診"
            else:
                note = None if s.id in open_ids else "已額滿"
            days.append(
                ClinicDayOut(
                    session_id=s.id,
                    date=s.date,
                    label=rules.date_label(s.date),
                    period=s.period,
                    period_label=f"{rules.PERIOD_LABELS[s.period]}門診",
                    status=s.status,
                    available=s.id in open_ids,
                    note=note,
                )
            )
        return days

    async def list_slots(self, session_id: UUID) -> list[SlotOut]:
        """選時段：這個門診每個看診時間的剩餘名額（即時查詢）。"""
        clinic = await self.repo.get_session(session_id)
        if clinic is None:
            raise NotFound("找不到這個門診", code="SESSION_NOT_FOUND")
        suspended = clinic.status is SessionStatus.SUSPENDED
        return [self._slot_out(slot, clinic.period, suspended) for slot in await self.repo.list_slots([clinic.id])]

    # ---------- 確認預約；我的預約 ----------

    async def book(self, user_id: UUID, elder_id: UUID, body: AppointmentCreate) -> AppointmentOut:
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        found = await self.repo.get_slot(body.slot_id)
        if found is None:
            raise NotFound("找不到這個看診時間", code="SLOT_NOT_FOUND")
        slot, clinic = found
        if await self.repo.has_booking(elder_id, clinic.id):
            raise Conflict("已經預約過這個門診", code="ALREADY_BOOKED")

        start, end = rules.booking_window(clock.today_taipei())
        visit_no = await self.repo.take_seat(slot.id, start, end)
        if visit_no is None:
            self._raise_unavailable(clinic, start, end)

        appointment = Appointment(elder_id=elder_id, session_id=clinic.id, slot_id=slot.id, visit_no=visit_no)
        try:
            await self.repo.add(appointment)
        except IntegrityError as exc:  # 同時送出兩次
            await self.session.rollback()
            raise Conflict("已經預約過這個門診", code="ALREADY_BOOKED") from exc
        await self.session.commit()
        return await self._get_out(elder_id, appointment.id)

    async def list_appointments(self, user_id: UUID, elder_id: UUID) -> list[AppointmentOut]:
        """我的預約：今天以後、還沒取消的預約。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        return [self._to_out(r) for r in await self.repo.list_upcoming(elder_id, clock.today_taipei())]

    async def cancel(self, user_id: UUID, elder_id: UUID, appointment_id: UUID) -> AppointmentOut:
        """取消後釋出名額（看診號碼不會重複發給別人）。重複取消不會出錯。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        row = await self._get_row(elder_id, appointment_id)
        appointment, slot, clinic = row[0], row[1], row[2]
        if appointment.status is AppointmentStatus.BOOKED:
            if clinic.date < clock.today_taipei():
                raise Conflict("已經過了看診日，不能取消", code="APPOINTMENT_PAST")
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = clock.now()
            await self.repo.release_seat(slot.id)
            await self.session.commit()
        return await self._get_out(elder_id, appointment_id)

    # ---------- 排程（/internal/tick 呼叫） ----------

    async def send_reminders(self, now: dt.datetime) -> int:
        """回診前一天 18:00 起，自動推播長輩與所有綁定家屬（各自的文字）。可重複呼叫而不重複推播。"""
        local = now.astimezone(clock.TAIPEI)
        if local.time() < rules.DAY_BEFORE_REMIND_AT:
            return 0
        claimed = await self.repo.claim_day_before(local.date() + dt.timedelta(days=1), now)
        await self.session.commit()

        for row in await self.repo.get_details(claimed):
            appointment, slot, _, doctor, department, hospital = row
            where = {"at": slot.time, "hospital": hospital.name, "department": department.name, "doctor": doctor.name}
            data = {"appointment_id": str(appointment.id), "map": self._map(hospital).model_dump_json()}
            name, gender = await self._elder_profile(appointment.elder_id)
            pushes = [([appointment.elder_id], PushType.APPOINTMENT_REMINDER, *rules.elder_reminder(**where))]
            if family_ids := await self.family.list_family_ids(appointment.elder_id):
                family_text = rules.family_reminder(elder_name=name, pronoun=pronoun(gender), **where)
                pushes.append((family_ids, PushType.APPOINTMENT_REMINDER, *family_text))
            for user_ids, type, title, body in pushes:
                try:
                    await self.notification.push(user_ids, type, title, body, data)
                except Exception:
                    logger.exception("預約提醒推播失敗 appointment_id=%s", appointment.id)
        return len(claimed)

    # ---------- 內部 ----------

    async def _last_visit(self, user_id: UUID, elder_id: UUID | None) -> LastVisit | None:
        if elder_id is None:
            return None
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        return await self.medication.last_visit(elder_id)

    async def _elder_profile(self, elder_id: UUID) -> tuple[str, str | None]:
        profile = await self.cards.elder_profile(elder_id)
        if profile is not None:
            return profile
        return (await self.auth.get_me(elder_id)).real_name, None

    async def _available_session_ids(self, sessions: list[ClinicSession]) -> set[UUID]:
        """開診且至少有一個時間還有名額的門診。"""
        open_sessions = {s.id for s in sessions if s.status is SessionStatus.OPEN}
        return {
            slot.session_id
            for slot in await self.repo.list_slots(list(open_sessions))
            if slot.booked_count < slot.capacity
        }

    @staticmethod
    def _raise_unavailable(clinic: ClinicSession, start: dt.date, end: dt.date) -> None:
        if clinic.status is SessionStatus.SUSPENDED:
            raise Conflict("這個門診停診", code="SESSION_SUSPENDED")
        if not start <= clinic.date <= end:
            raise Conflict("只能預約明天起 2 週內的門診", code="SESSION_OUT_OF_RANGE")
        raise Conflict("這個時間已額滿", code="SLOT_FULL")

    async def _get_row(self, elder_id: UUID, appointment_id: UUID) -> AppointmentRow:
        row = await self.repo.get_detail(elder_id, appointment_id)
        if row is None:
            raise NotFound("找不到這個預約", code="APPOINTMENT_NOT_FOUND")
        return row

    async def _get_out(self, elder_id: UUID, appointment_id: UUID) -> AppointmentOut:
        # 重新查詢，拿到 commit 後的狀態
        self.session.expire_all()
        return self._to_out(await self._get_row(elder_id, appointment_id))

    @staticmethod
    def _map(hospital: Hospital) -> LaunchMapMessage:
        return LaunchMapMessage.to_address(hospital.address)

    def _hospital_out(self, hospital: Hospital) -> HospitalOut:
        return HospitalOut(id=hospital.id, name=hospital.name, address=hospital.address, map=self._map(hospital))

    @staticmethod
    def _slot_out(slot: ClinicSlot, period, suspended: bool) -> SlotOut:
        remaining = 0 if suspended else max(slot.capacity - slot.booked_count, 0)
        return SlotOut(
            slot_id=slot.id,
            time=slot.time,
            label=rules.time_label(period, slot.time),
            remaining=remaining,
            available=remaining > 0,
            note="停診" if suspended else rules.remaining_label(remaining),
        )

    def _to_out(self, row: AppointmentRow) -> AppointmentOut:
        appointment, slot, clinic, doctor, department, hospital = row
        return AppointmentOut(
            id=appointment.id,
            hospital=self._hospital_out(hospital),
            department=department.name,
            doctor=doctor.name,
            date=clinic.date,
            date_label=rules.date_label(clinic.date),
            time=slot.time,
            time_label=rules.time_label(clinic.period, slot.time),
            period=clinic.period,
            visit_no=appointment.visit_no,
            status=appointment.status,
            message=BOOKED_MESSAGE,
        )
