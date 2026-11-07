import datetime as dt
from uuid import UUID

from sqlalchemy import Row, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointment.models import (
    Appointment,
    AppointmentStatus,
    ClinicSession,
    ClinicSlot,
    Department,
    Doctor,
    Hospital,
    SessionStatus,
)

# 一筆預約連同看診時間、門診、醫師、科別、院區
AppointmentRow = Row[tuple[Appointment, ClinicSlot, ClinicSession, Doctor, Department, Hospital]]


class AppointmentRepository:
    """院區、科別、醫師、門診（比賽時為模擬資料）與預約的存取。

    正式版院區、門診改由 integrations/tpech 查詢聯醫，預約紀錄仍存在這裡。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- 院區、科別、醫師、門診 ----------

    async def list_hospitals(self) -> list[Hospital]:
        return list(await self.session.scalars(select(Hospital).order_by(Hospital.name)))

    async def get_hospital(self, hospital_id: UUID) -> Hospital | None:
        return await self.session.get(Hospital, hospital_id)

    async def list_departments(self, hospital_id: UUID) -> list[Department]:
        stmt = select(Department).where(Department.hospital_id == hospital_id).order_by(Department.name)
        return list(await self.session.scalars(stmt))

    async def get_department(self, department_id: UUID) -> Department | None:
        return await self.session.get(Department, department_id)

    async def list_doctors(self, department_id: UUID) -> list[Doctor]:
        stmt = select(Doctor).where(Doctor.department_id == department_id).order_by(Doctor.name)
        return list(await self.session.scalars(stmt))

    async def get_doctor(self, doctor_id: UUID) -> Doctor | None:
        return await self.session.get(Doctor, doctor_id)

    async def list_sessions(self, doctor_ids: list[UUID], start: dt.date, end: dt.date) -> list[ClinicSession]:
        if not doctor_ids:
            return []
        stmt = (
            select(ClinicSession)
            .where(ClinicSession.doctor_id.in_(doctor_ids), ClinicSession.date.between(start, end))
            .order_by(ClinicSession.date, ClinicSession.period)
        )
        return list(await self.session.scalars(stmt))

    async def get_session(self, session_id: UUID) -> ClinicSession | None:
        return await self.session.get(ClinicSession, session_id)

    async def list_slots(self, session_ids: list[UUID]) -> list[ClinicSlot]:
        if not session_ids:
            return []
        stmt = select(ClinicSlot).where(ClinicSlot.session_id.in_(session_ids)).order_by(ClinicSlot.time)
        return list(await self.session.scalars(stmt))

    async def get_slot(self, slot_id: UUID) -> tuple[ClinicSlot, ClinicSession] | None:
        stmt = (
            select(ClinicSlot, ClinicSession)
            .join(ClinicSession, ClinicSlot.session_id == ClinicSession.id)
            .where(ClinicSlot.id == slot_id)
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def take_seat(self, slot_id: UUID, start: dt.date, end: dt.date) -> int | None:
        """門診開放、這個時間未額滿、在可預約期間內時佔一個名額，回傳看診號碼；否則回傳 None。

        佔名額用一條 UPDATE … WHERE booked_count < capacity，同時搶最後一個名額只有一人成功；
        號碼由門診只增不減的 issued_count 發出，取消後也不會重複。
        """
        open_sessions = select(ClinicSession.id).where(
            ClinicSession.status == SessionStatus.OPEN, ClinicSession.date.between(start, end)
        )
        session_id = await self.session.scalar(
            update(ClinicSlot)
            .where(
                ClinicSlot.id == slot_id,
                ClinicSlot.booked_count < ClinicSlot.capacity,
                ClinicSlot.session_id.in_(open_sessions),
            )
            .values(booked_count=ClinicSlot.booked_count + 1)
            .returning(ClinicSlot.session_id)
        )
        if session_id is None:
            return None
        return await self.session.scalar(
            update(ClinicSession)
            .where(ClinicSession.id == session_id)
            .values(issued_count=ClinicSession.issued_count + 1)
            .returning(ClinicSession.issued_count)
        )

    async def release_seat(self, slot_id: UUID) -> None:
        await self.session.execute(
            update(ClinicSlot)
            .where(ClinicSlot.id == slot_id, ClinicSlot.booked_count > 0)
            .values(booked_count=ClinicSlot.booked_count - 1)
        )

    # ---------- 預約 ----------

    def _detail_query(self):
        return (
            select(Appointment, ClinicSlot, ClinicSession, Doctor, Department, Hospital)
            .join(ClinicSlot, Appointment.slot_id == ClinicSlot.id)
            .join(ClinicSession, Appointment.session_id == ClinicSession.id)
            .join(Doctor, ClinicSession.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Hospital, Department.hospital_id == Hospital.id)
        )

    async def add(self, appointment: Appointment) -> None:
        self.session.add(appointment)
        await self.session.flush()

    async def has_booking(self, elder_id: UUID, session_id: UUID) -> bool:
        stmt = select(Appointment.id).where(
            Appointment.elder_id == elder_id,
            Appointment.session_id == session_id,
            Appointment.status == AppointmentStatus.BOOKED,
        )
        return await self.session.scalar(stmt) is not None

    async def get_detail(self, elder_id: UUID, appointment_id: UUID) -> AppointmentRow | None:
        stmt = self._detail_query().where(Appointment.id == appointment_id, Appointment.elder_id == elder_id)
        return (await self.session.execute(stmt)).first()

    async def list_upcoming(self, elder_id: UUID, today: dt.date) -> list[AppointmentRow]:
        stmt = (
            self._detail_query()
            .where(
                Appointment.elder_id == elder_id,
                Appointment.status == AppointmentStatus.BOOKED,
                ClinicSession.date >= today,
            )
            .order_by(ClinicSession.date, ClinicSlot.time)
        )
        return list((await self.session.execute(stmt)).all())

    # ---------- 提醒（排程用） ----------

    async def claim_day_before(self, tomorrow: dt.date, now: dt.datetime) -> list[UUID]:
        """領取明天的預約（還沒提醒過），標記已提醒。"""
        stmt = (
            update(Appointment)
            .where(
                Appointment.session_id == ClinicSession.id,
                ClinicSession.date == tomorrow,
                Appointment.status == AppointmentStatus.BOOKED,
                Appointment.reminded_day_before_at.is_(None),
            )
            .values(reminded_day_before_at=now)
            .returning(Appointment.id)
        )
        return list(await self.session.scalars(stmt))

    async def get_details(self, appointment_ids: list[UUID]) -> list[AppointmentRow]:
        if not appointment_ids:
            return []
        stmt = self._detail_query().where(Appointment.id.in_(appointment_ids))
        return list((await self.session.execute(stmt)).all())
