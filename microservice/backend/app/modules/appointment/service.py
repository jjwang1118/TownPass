from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotImplementedYet
from app.modules.appointment.repository import AppointmentRepository
from app.modules.appointment.schemas import (
    AppointmentCreate,
    AppointmentOut,
    DepartmentOut,
    DoctorOut,
    HospitalOut,
    SessionOut,
)


class AppointmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AppointmentRepository(session)

    async def list_hospitals(self) -> list[HospitalOut]:
        raise NotImplementedYet()

    async def list_departments(self, hospital_id: UUID, elder_id: UUID | None) -> list[DepartmentOut]:
        """elder_id 有值時，從藥區找上次看的科別排第一。"""
        raise NotImplementedYet()

    async def list_doctors(self, department_id: UUID, elder_id: UUID | None) -> list[DoctorOut]:
        raise NotImplementedYet()

    async def list_sessions(self, doctor_id: UUID) -> list[SessionOut]:
        """未來 2 週的門診。"""
        raise NotImplementedYet()

    async def book(self, user_id: UUID, elder_id: UUID, body: AppointmentCreate) -> AppointmentOut:
        raise NotImplementedYet()

    async def list_appointments(self, user_id: UUID, elder_id: UUID) -> list[AppointmentOut]:
        raise NotImplementedYet()

    async def cancel(self, user_id: UUID, elder_id: UUID, appointment_id: UUID) -> AppointmentOut:
        raise NotImplementedYet()
