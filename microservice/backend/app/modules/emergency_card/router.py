from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.emergency_card.models import ConsentType
from app.modules.emergency_card.schemas import (
    CardCodeOut,
    CardOut,
    CardUpdate,
    CommonItemsOut,
    ConsentCreate,
    ConsentOut,
)
from app.modules.emergency_card.service import EmergencyCardService

router = APIRouter(tags=["emergency_card"])


def get_service(session: SessionDep) -> EmergencyCardService:
    return EmergencyCardService(session)


Service = Annotated[EmergencyCardService, Depends(get_service)]


@router.get("/emergency-card/common-items", response_model=CommonItemsOut)
async def common_items() -> CommonItemsOut:
    return EmergencyCardService.common_items()


@router.post("/elders/{elder_id}/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    elder_id: UUID, body: ConsentCreate, user_id: CurrentUserId, service: Service
) -> ConsentOut:
    return await service.grant_consent(user_id, elder_id, body.type)


@router.delete("/elders/{elder_id}/consents/{consent_type}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    elder_id: UUID, consent_type: ConsentType, user_id: CurrentUserId, service: Service
) -> None:
    await service.revoke_consent(user_id, elder_id, consent_type)


@router.get("/elders/{elder_id}/emergency-card", response_model=CardOut)
async def get_card(elder_id: UUID, user_id: CurrentUserId, service: Service) -> CardOut:
    return await service.get_card(user_id, elder_id)


@router.put("/elders/{elder_id}/emergency-card", response_model=CardOut)
async def update_card(elder_id: UUID, body: CardUpdate, user_id: CurrentUserId, service: Service) -> CardOut:
    """儲存整張卡，含一位緊急聯絡人（UI E14）。"""
    return await service.update_card(user_id, elder_id, body)


@router.post("/elders/{elder_id}/emergency-card/regenerate-code", response_model=CardCodeOut)
async def regenerate_code(elder_id: UUID, user_id: CurrentUserId, service: Service) -> CardCodeOut:
    return await service.regenerate_code(user_id, elder_id)
