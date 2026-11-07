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
    ReminderToggle,
)
from app.modules.appointment.service import AppointmentService

router = APIRouter(tags=["appointment"])


def get_service(session: SessionDep) -> AppointmentService:
    return AppointmentService(session)


Service = Annotated[AppointmentService, Depends(get_service)]
OptionalElder = Annotated[UUID | None, Query(description="帶入時，上次看的科別、醫師會排第一並標記")]


@router.get("/hospitals", response_model=list[HospitalOut])
async def list_hospitals(_: CurrentUserId, service: Service) -> list[HospitalOut]:
    """步驟 1：選院區（限臺北市立聯合醫院）。"""
    return await service.list_hospitals()


@router.get("/hospitals/{hospital_id}/departments", response_model=list[DepartmentOut])
async def list_departments(
    hospital_id: UUID, user_id: CurrentUserId, service: Service, elder_id: OptionalElder = None
) -> list[DepartmentOut]:
    """步驟 2：選科別。"""
    return await service.list_departments(user_id, hospital_id, elder_id)


@router.get("/departments/{department_id}/doctors", response_model=list[DoctorOut])
async def list_doctors(
    department_id: UUID, user_id: CurrentUserId, service: Service, elder_id: OptionalElder = None
) -> list[DoctorOut]:
    """步驟 3：選醫師。"""
    return await service.list_doctors(user_id, department_id, elder_id)


@router.get("/doctors/{doctor_id}/sessions", response_model=list[ClinicDayOut])
async def list_clinic_days(doctor_id: UUID, _: CurrentUserId, service: Service) -> list[ClinicDayOut]:
    """步驟 4、5：未來 2 週有門診的日子，每天的上午、下午、晚上時段。"""
    return await service.list_clinic_days(doctor_id)


@router.post(
    "/elders/{elder_id}/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED
)
async def book(
    elder_id: UUID, body: AppointmentCreate, user_id: CurrentUserId, service: Service
) -> AppointmentOut:
    """步驟 6：確認預約；回傳完成頁內容。"""
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


@router.put("/elders/{elder_id}/appointments/{appointment_id}/reminder", response_model=AppointmentOut)
async def set_reminder(
    elder_id: UUID, appointment_id: UUID, body: ReminderToggle, user_id: CurrentUserId, service: Service
) -> AppointmentOut:
    """完成頁「加入提醒」：前一天 18:00、當天 08:00 推播長輩與家人。"""
    return await service.set_reminder(user_id, elder_id, appointment_id, body.enabled)
