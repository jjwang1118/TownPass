import datetime as dt
import logging
from itertools import groupby
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
    Hospital,
    Period,
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
    SessionOut,
)
from app.modules.family.service import Access, FamilyService
from app.modules.medication.service import MedicationService
from app.modules.notification.schemas import PushType
from app.modules.notification.service import NotificationService

logger = logging.getLogger(__name__)

_PERIOD_ORDER = {Period.MORNING: 0, Period.AFTERNOON: 1, Period.EVENING: 2}


class AppointmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AppointmentRepository(session)
        self.family = FamilyService(session)
        self.medication = MedicationService(session)
        self.notification = NotificationService(session)

    # ---------- 步驟 1～5：選院區、科別、醫師、日期、時段 ----------

    async def list_hospitals(self) -> list[HospitalOut]:
        return [self._hospital_out(h) for h in await self.repo.list_hospitals()]

    async def list_departments(self, user_id: UUID, hospital_id: UUID, elder_id: UUID | None) -> list[DepartmentOut]:
        """elder_id 有值時，藥區「上次看的科別」排第一個。"""
        if await self.repo.get_hospital(hospital_id) is None:
            raise NotFound("找不到這個院區", code="HOSPITAL_NOT_FOUND")
        last = await self._last_visit(user_id, elder_id)
        departments = [
            DepartmentOut(id=d.id, name=d.name, last_visited=last is not None and d.name == last.department)
            for d in await self.repo.list_departments(hospital_id)
        ]
        return sorted(departments, key=lambda d: not d.last_visited)  # 穩定排序，其餘維持原順序

    async def list_doctors(self, user_id: UUID, department_id: UUID, elder_id: UUID | None) -> list[DoctorOut]:
        """elder_id 有值時，標記上次看診的醫師（同科別、同名），前端預設選取。"""
        department = await self.repo.get_department(department_id)
        if department is None:
            raise NotFound("找不到這個科別", code="DEPARTMENT_NOT_FOUND")
        last = await self._last_visit(user_id, elder_id)
        same_department = last is not None and last.department == department.name
        doctors = [
            DoctorOut(id=d.id, name=d.name, last_visited=same_department and d.name == last.doctor)  # type: ignore[union-attr]
            for d in await self.repo.list_doctors(department_id)
        ]
        return sorted(doctors, key=lambda d: not d.last_visited)

    async def list_clinic_days(self, doctor_id: UUID) -> list[ClinicDayOut]:
        """未來 2 週（明天起）這位醫師有門診的日子與時段；額滿、停診標示不可選。"""
        if await self.repo.get_doctor(doctor_id) is None:
            raise NotFound("找不到這位醫師", code="DOCTOR_NOT_FOUND")
        start, end = rules.booking_window(clock.today_taipei())
        sessions = sorted(
            await self.repo.list_sessions(doctor_id, start, end), key=lambda s: (s.date, _PERIOD_ORDER[s.period])
        )
        days = []
        for day, group in groupby(sessions, key=lambda s: s.date):
            items = [self._session_out(s) for s in group]
            days.append(
                ClinicDayOut(
                    date=day,
                    label=rules.date_label(day),
                    available=any(i.available for i in items),
                    sessions=items,
                )
            )
        return days

    # ---------- 步驟 6：確認預約；我的預約 ----------

    async def book(self, user_id: UUID, elder_id: UUID, body: AppointmentCreate) -> AppointmentOut:
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        clinic = await self.repo.get_session(body.session_id)
        if clinic is None:
            raise NotFound("找不到這個門診", code="SESSION_NOT_FOUND")
        if await self.repo.has_booking(elder_id, clinic.id):
            raise Conflict("已經預約過這個門診", code="ALREADY_BOOKED")

        start, end = rules.booking_window(clock.today_taipei())
        visit_no = await self.repo.take_number(clinic.id, start, end)
        if visit_no is None:
            await self._raise_unavailable(clinic, start, end)

        appointment = Appointment(elder_id=elder_id, session_id=clinic.id, visit_no=visit_no)
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
        rows = await self.repo.list_upcoming(elder_id, clock.today_taipei())
        rows.sort(key=lambda r: (r[1].date, _PERIOD_ORDER[r[1].period]))
        return [self._to_out(r) for r in rows]

    async def cancel(self, user_id: UUID, elder_id: UUID, appointment_id: UUID) -> AppointmentOut:
        """取消後釋出名額（看診號碼不會重複發給別人）。重複取消不會出錯。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        row = await self._get_row(elder_id, appointment_id)
        appointment, clinic = row[0], row[1]
        if appointment.status is AppointmentStatus.BOOKED:
            if clinic.date < clock.today_taipei():
                raise Conflict("已經過了看診日，不能取消", code="APPOINTMENT_PAST")
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = clock.now()
            await self.repo.release_seat(clinic.id)
            await self.session.commit()
        return await self._get_out(elder_id, appointment_id)

    async def set_reminder(self, user_id: UUID, elder_id: UUID, appointment_id: UUID, enabled: bool) -> AppointmentOut:
        """完成頁「加入提醒」：前一天 18:00、當天 08:00 推播長輩與家人。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        row = await self._get_row(elder_id, appointment_id)
        if row[0].status is not AppointmentStatus.BOOKED:
            raise Conflict("這個預約已經取消", code="APPOINTMENT_CANCELLED")
        row[0].reminder_enabled = enabled
        await self.session.commit()
        return await self._get_out(elder_id, appointment_id)

    # ---------- 排程（/internal/tick 呼叫） ----------

    async def send_reminders(self, now: dt.datetime) -> int:
        """前一天 18:00 起、當天 08:00 起，各提醒一次。可重複呼叫而不重複推播。"""
        local = now.astimezone(clock.TAIPEI)
        today = local.date()
        claimed: list[tuple[UUID, str]] = []
        if local.time() >= rules.DAY_BEFORE_REMIND_AT:
            claimed += [(i, "明天") for i in await self.repo.claim_day_before(today + dt.timedelta(days=1), now)]
        if local.time() >= rules.SAME_DAY_REMIND_AT:
            claimed += [(i, "今天") for i in await self.repo.claim_same_day(today, now)]
        await self.session.commit()

        when_by_id = dict(claimed)
        for row in await self.repo.get_details(list(when_by_id)):
            appointment, clinic, doctor, department, hospital = row
            text = rules.appointment_reminder_text(
                when=when_by_id[appointment.id],
                hospital=hospital.name,
                department=department.name,
                doctor=doctor.name,
                period=clinic.period,
                visit_no=appointment.visit_no,
            )
            recipients = [appointment.elder_id, *await self.family.list_family_ids(appointment.elder_id)]
            try:
                await self.notification.push(
                    recipients,
                    PushType.APPOINTMENT_REMINDER,
                    "回診提醒",
                    text,
                    {"appointment_id": str(appointment.id), "map": self._map(hospital).model_dump_json()},
                )
            except Exception:
                logger.exception("預約提醒推播失敗 appointment_id=%s", appointment.id)
        return len(claimed)

    # ---------- 內部 ----------

    async def _last_visit(self, user_id: UUID, elder_id: UUID | None):
        if elder_id is None:
            return None
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        return await self.medication.last_visit(elder_id)

    async def _raise_unavailable(self, clinic: ClinicSession, start: dt.date, end: dt.date) -> None:
        if clinic.status is SessionStatus.SUSPENDED:
            raise Conflict("這個時段停診", code="SESSION_SUSPENDED")
        if not start <= clinic.date <= end:
            raise Conflict("只能預約明天起 2 週內的門診", code="SESSION_OUT_OF_RANGE")
        raise Conflict("這個時段已額滿", code="SESSION_FULL")

    async def _get_row(self, elder_id: UUID, appointment_id: UUID) -> AppointmentRow:
        row = await self.repo.get_detail(elder_id, appointment_id)
        if row is None:
            raise NotFound("找不到這個預約", code="APPOINTMENT_NOT_FOUND")
        return row

    async def _get_out(self, elder_id: UUID, appointment_id: UUID) -> AppointmentOut:
        # 重新查詢，拿到 commit 後的門診與預約狀態
        self.session.expire_all()
        return self._to_out(await self._get_row(elder_id, appointment_id))

    @staticmethod
    def _map(hospital: Hospital) -> LaunchMapMessage:
        return LaunchMapMessage.to_address(hospital.address)

    def _hospital_out(self, hospital: Hospital) -> HospitalOut:
        return HospitalOut(id=hospital.id, name=hospital.name, address=hospital.address, map=self._map(hospital))

    @staticmethod
    def _session_out(clinic: ClinicSession) -> SessionOut:
        return SessionOut(
            session_id=clinic.id,
            period=clinic.period,
            label=rules.PERIOD_LABELS[clinic.period],
            status=clinic.status,
            available=clinic.status is SessionStatus.OPEN and clinic.booked_count < clinic.capacity,
        )

    def _to_out(self, row: AppointmentRow) -> AppointmentOut:
        appointment, clinic, doctor, department, hospital = row
        return AppointmentOut(
            id=appointment.id,
            hospital=self._hospital_out(hospital),
            department=department.name,
            doctor=doctor.name,
            date=clinic.date,
            date_label=rules.date_label(clinic.date),
            period=clinic.period,
            period_label=rules.PERIOD_LABELS[clinic.period],
            visit_no=appointment.visit_no,
            status=appointment.status,
            reminder_enabled=appointment.reminder_enabled,
        )
