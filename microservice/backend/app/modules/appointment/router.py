from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.appointment.schemas import (
    AppointmentCreate,
    AppointmentOut,
    DepartmentOut,
    DoctorOut,
    HospitalOut,
    SessionOut,
)
from app.modules.appointment.service import AppointmentService

router = APIRouter(tags=["appointment"])


def get_service(session: SessionDep) -> AppointmentService:
    return AppointmentService(session)


Service = Annotated[AppointmentService, Depends(get_service)]


@router.get("/hospitals", response_model=list[HospitalOut])
async def list_hospitals(_: CurrentUserId, service: Service) -> list[HospitalOut]:
    return await service.list_hospitals()


@router.get("/hospitals/{hospital_id}/departments", response_model=list[DepartmentOut])
async def list_departments(
    hospital_id: UUID, _: CurrentUserId, service: Service, elder_id: UUID | None = None
) -> list[DepartmentOut]:
    return await service.list_departments(hospital_id, elder_id)


@router.get("/departments/{department_id}/doctors", response_model=list[DoctorOut])
async def list_doctors(
    department_id: UUID, _: CurrentUserId, service: Service, elder_id: UUID | None = None
) -> list[DoctorOut]:
    return await service.list_doctors(department_id, elder_id)


@router.get("/doctors/{doctor_id}/sessions", response_model=list[SessionOut])
async def list_sessions(doctor_id: UUID, _: CurrentUserId, service: Service) -> list[SessionOut]:
    return await service.list_sessions(doctor_id)


@router.post(
    "/elders/{elder_id}/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED
)
async def book(
    elder_id: UUID, body: AppointmentCreate, user_id: CurrentUserId, service: Service
) -> AppointmentOut:
    return await service.book(user_id, elder_id, body)


@router.get("/elders/{elder_id}/appointments", response_model=list[AppointmentOut])
async def list_appointments(elder_id: UUID, user_id: CurrentUserId, service: Service) -> list[AppointmentOut]:
    return await service.list_appointments(user_id, elder_id)


@router.post("/elders/{elder_id}/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel(
    elder_id: UUID, appointment_id: UUID, user_id: CurrentUserId, service: Service
) -> AppointmentOut:
    return await service.cancel(user_id, elder_id, appointment_id)
