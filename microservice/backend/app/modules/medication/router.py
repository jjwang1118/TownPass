from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.medication.schemas import (
    MedicationCreate,
    MedicationCreated,
    MedicationOut,
    MedicationUpdate,
    NextDoseOut,
    QrPreviewIn,
    QrPreviewOut,
    TimeSlotItem,
    TimeSlotsUpdate,
)
from app.modules.medication.service import MedicationService

router = APIRouter(prefix="/elders/{elder_id}", tags=["medication"])


def get_service(session: SessionDep) -> MedicationService:
    return MedicationService(session)


Service = Annotated[MedicationService, Depends(get_service)]


@router.get("/medications", response_model=list[MedicationOut])
async def list_medications(elder_id: UUID, user_id: CurrentUserId, service: Service) -> list[MedicationOut]:
    return await service.list_medications(user_id, elder_id)


@router.post("/medications/qr-preview", response_model=QrPreviewOut)
async def preview_qr(elder_id: UUID, body: QrPreviewIn, user_id: CurrentUserId, service: Service) -> QrPreviewOut:
    """body 為 App 對 { name: 'qr_code_scan' } 的回覆；只解析，不寫入。"""
    return await service.preview_qr(user_id, elder_id, body.data)


@router.post("/medications", response_model=MedicationCreated, status_code=status.HTTP_201_CREATED)
async def create_medication(
    elder_id: UUID, body: MedicationCreate, user_id: CurrentUserId, service: Service
) -> MedicationCreated:
    return await service.create(user_id, elder_id, body)


@router.get("/medications/{medication_id}", response_model=MedicationOut)
async def get_medication(
    elder_id: UUID, medication_id: UUID, user_id: CurrentUserId, service: Service
) -> MedicationOut:
    return await service.get(user_id, elder_id, medication_id)


@router.patch("/medications/{medication_id}", response_model=MedicationOut)
async def update_medication(
    elder_id: UUID, medication_id: UUID, body: MedicationUpdate, user_id: CurrentUserId, service: Service
) -> MedicationOut:
    return await service.update(user_id, elder_id, medication_id, body)


@router.post("/medications/{medication_id}/stop", response_model=MedicationOut)
async def stop_medication(
    elder_id: UUID, medication_id: UUID, user_id: CurrentUserId, service: Service
) -> MedicationOut:
    return await service.stop(user_id, elder_id, medication_id)


@router.get("/time-slots", response_model=list[TimeSlotItem])
async def list_time_slots(elder_id: UUID, user_id: CurrentUserId, service: Service) -> list[TimeSlotItem]:
    return await service.list_time_slots(user_id, elder_id)


@router.put("/time-slots", response_model=list[TimeSlotItem])
async def update_time_slots(
    elder_id: UUID, body: TimeSlotsUpdate, user_id: CurrentUserId, service: Service
) -> list[TimeSlotItem]:
    return await service.update_time_slots(user_id, elder_id, body)


@router.get("/next-dose", response_model=NextDoseOut | None)
async def next_dose(elder_id: UUID, user_id: CurrentUserId, service: Service) -> NextDoseOut | None:
    """首頁狀態列「下一次吃藥：今天 12:00」。"""
    return await service.next_dose(user_id, elder_id)
