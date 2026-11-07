from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.appointment.schemas import (
    AppointmentCreate,
    AppointmentOut,
    ClinicDayOut,
    DepartmentOut,
    DoctorOut,
    HospitalOut,
    SlotOut,
)
from app.modules.appointment.service import AppointmentService

router = APIRouter(tags=["appointment"])


def get_service(session: SessionDep) -> AppointmentService:
    return AppointmentService(session)


Service = Annotated[AppointmentService, Depends(get_service)]
OptionalElder = Annotated[UUID | None, Query(description="帶入時，最近藥單的科別、醫師會排第一並標記")]


@router.get("/hospitals", response_model=list[HospitalOut])
async def list_hospitals(_: CurrentUserId, service: Service) -> list[HospitalOut]:
    """選院區（限臺北市立聯合醫院，9 個院址）。"""
    return await service.list_hospitals()


@router.get("/hospitals/{hospital_id}/departments", response_model=list[DepartmentOut])
async def list_departments(
    hospital_id: UUID, user_id: CurrentUserId, service: Service, elder_id: OptionalElder = None
) -> list[DepartmentOut]:
    """選科別：從藥單帶入的科別排第一（from_letter）。"""
    return await service.list_departments(user_id, hospital_id, elder_id)


@router.get("/departments/{department_id}/doctors", response_model=list[DoctorOut])
async def list_doctors(
    department_id: UUID, user_id: CurrentUserId, service: Service, elder_id: OptionalElder = None
) -> list[DoctorOut]:
    """選醫師：門診時間；額滿為灰色不可選。"""
    return await service.list_doctors(user_id, department_id, elder_id)


@router.get("/doctors/{doctor_id}/sessions", response_model=list[ClinicDayOut])
async def list_clinic_days(doctor_id: UUID, _: CurrentUserId, service: Service) -> list[ClinicDayOut]:
    """選日期：明天起 2 週這位醫師的門診日（例如 11/14（五）上午門診）。"""
    return await service.list_clinic_days(doctor_id)


@router.get("/sessions/{session_id}/slots", response_model=list[SlotOut])
async def list_slots(session_id: UUID, _: CurrentUserId, service: Service) -> list[SlotOut]:
    """選時段：每個看診時間（例如上午 09:30）的剩餘名額。"""
    return await service.list_slots(session_id)


@router.post(
    "/elders/{elder_id}/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED
)
async def book(
    elder_id: UUID, body: AppointmentCreate, user_id: CurrentUserId, service: Service
) -> AppointmentOut:
    """確認預約：body 為選好的看診時間；回傳預約成功頁內容（看診號碼）。"""
    return await service.book(user_id, elder_id, body)


@router.get("/elders/{elder_id}/appointments", response_model=list[AppointmentOut])
async def list_appointments(elder_id: UUID, user_id: CurrentUserId, service: Service) -> list[AppointmentOut]:
    """我的預約：今天以後、還沒取消的預約。"""
    return await service.list_appointments(user_id, elder_id)


@router.post("/elders/{elder_id}/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel(
    elder_id: UUID, appointment_id: UUID, user_id: CurrentUserId, service: Service
) -> AppointmentOut:
    return await service.cancel(user_id, elder_id, appointment_id)
