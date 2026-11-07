import datetime as dt
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.medication.models import PrescriptionStatus
from app.modules.medication.schemas import (
    DrugSearchItem,
    MedicationOut,
    MedicationStop,
    MedicationUpdate,
    NextDoseOut,
    PhotoIn,
    PrescriptionCreate,
    PrescriptionCreated,
    PrescriptionDraft,
    PrescriptionOut,
    PrescriptionUpdate,
    PreviewOut,
    QrPreviewIn,
    TodayOut,
)
from app.modules.medication.service import MedicationService

router = APIRouter(tags=["medication"])
elder = APIRouter(prefix="/elders/{elder_id}")


def get_service(session: SessionDep) -> MedicationService:
    return MedicationService(session)


Service = Annotated[MedicationService, Depends(get_service)]


# ---------- 藥名搜尋 ----------


@router.get("/drugs/search", response_model=list[DrugSearchItem])
async def search_drugs(
    _: CurrentUserId, service: Service, q: Annotated[str, Query(max_length=64, examples=["Asp", "阿斯"])]
) -> list[DrugSearchItem]:
    """手動新增、修改藥品的藥名清單。打 2 個字以上才有結果，最多 8 筆。"""
    return await service.search_drugs(q)


# ---------- 新增藥單：三條路徑先預覽，核對後加入 ----------


@elder.post("/prescriptions/qr-preview", response_model=PreviewOut)
async def preview_qr(elder_id: UUID, body: QrPreviewIn, user_id: CurrentUserId, service: Service) -> PreviewOut:
    """掃藥袋 QR Code：body 為 App 對 { name: 'qr_code_scan' } 的回覆。不寫入。"""
    return await service.preview_qr(user_id, elder_id, body.data)


@elder.post("/prescriptions/photo-preview", response_model=PreviewOut)
async def preview_photo(elder_id: UUID, body: PhotoIn, user_id: CurrentUserId, service: Service) -> PreviewOut:
    """拍藥袋照片：body 為 App 裝置端模型整理出的欄位。回傳比對結果與每個欄位的信心分數。不寫入。"""
    return await service.preview_photo(user_id, elder_id, body)


@elder.post("/prescriptions/preview", response_model=PreviewOut)
async def preview(
    elder_id: UUID, body: PrescriptionDraft, user_id: CurrentUserId, service: Service
) -> PreviewOut:
    """手動新增，或修改後「再看一次」：檢查同成分、排出吃藥時間。不寫入。"""
    return await service.preview(user_id, elder_id, body)


@elder.post("/prescriptions", response_model=PrescriptionCreated, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    elder_id: UUID, body: PrescriptionCreate, user_id: CurrentUserId, service: Service
) -> PrescriptionCreated:
    """「確認無誤，加入藥單」：body 為預覽回傳的 draft（可修改後送出）。"""
    return await service.create(user_id, elder_id, body)


# ---------- 我的藥單 ----------


@elder.get("/prescriptions", response_model=list[PrescriptionOut])
async def list_prescriptions(
    elder_id: UUID,
    user_id: CurrentUserId,
    service: Service,
    status_: Annotated[PrescriptionStatus, Query(alias="status")] = PrescriptionStatus.ACTIVE,
) -> list[PrescriptionOut]:
    """吃藥中（依字母）或已吃完（新的在前）。"""
    return await service.list_prescriptions(user_id, elder_id, status_)


@elder.get("/prescriptions/{prescription_id}", response_model=PrescriptionOut)
async def get_prescription(
    elder_id: UUID, prescription_id: UUID, user_id: CurrentUserId, service: Service
) -> PrescriptionOut:
    return await service.get_prescription(user_id, elder_id, prescription_id)


@elder.patch("/prescriptions/{prescription_id}", response_model=PrescriptionOut)
async def update_prescription(
    elder_id: UUID, prescription_id: UUID, body: PrescriptionUpdate, user_id: CurrentUserId, service: Service
) -> PrescriptionOut:
    """補填院區、科別、醫師，或修改看診日、天數。"""
    return await service.update_prescription(user_id, elder_id, prescription_id, body)


@elder.post("/prescriptions/{prescription_id}/finish", response_model=PrescriptionOut)
async def finish_prescription(
    elder_id: UUID, prescription_id: UUID, user_id: CurrentUserId, service: Service
) -> PrescriptionOut:
    """提早移到「已吃完」，字母釋放。"""
    return await service.finish_prescription(user_id, elder_id, prescription_id)


# ---------- 藥品 ----------


@elder.get("/medications/{medication_id}", response_model=MedicationOut)
async def get_medication(
    elder_id: UUID, medication_id: UUID, user_id: CurrentUserId, service: Service
) -> MedicationOut:
    return await service.get_medication(user_id, elder_id, medication_id)


@elder.patch("/medications/{medication_id}", response_model=MedicationOut)
async def update_medication(
    elder_id: UUID, medication_id: UUID, body: MedicationUpdate, user_id: CurrentUserId, service: Service
) -> MedicationOut:
    return await service.update_medication(user_id, elder_id, medication_id, body)


@elder.post("/medications/{medication_id}/stop", response_model=MedicationOut)
async def stop_medication(
    elder_id: UUID, medication_id: UUID, body: MedicationStop, user_id: CurrentUserId, service: Service
) -> MedicationOut:
    return await service.stop_medication(user_id, elder_id, medication_id, body.reason)


# ---------- 今天、下一次吃藥 ----------


@elder.get("/today", response_model=TodayOut)
async def today(
    elder_id: UUID, user_id: CurrentUserId, service: Service, date: Annotated[dt.date | None, Query()] = None
) -> TodayOut:
    """今天四個時段（09:00、12:00、18:00、22:00）的藥；沒有藥的時段不列出。"""
    return await service.today(user_id, elder_id, date)


@elder.get("/next-dose", response_model=NextDoseOut | None)
async def next_dose(elder_id: UUID, user_id: CurrentUserId, service: Service) -> NextDoseOut | None:
    """首頁「下一次吃藥」。"""
    return await service.next_dose(user_id, elder_id)


router.include_router(elder)
