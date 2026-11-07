from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUserId, SessionDep
from app.modules.family.schemas import BindingCreate, BindingOut, BindingUpdate, InviteOut
from app.modules.family.service import FamilyService

router = APIRouter(prefix="/family", tags=["family"])


def get_service(session: SessionDep) -> FamilyService:
    return FamilyService(session)


Service = Annotated[FamilyService, Depends(get_service)]


@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(user_id: CurrentUserId, service: Service) -> InviteOut:
    return await service.create_invite(user_id)


@router.post("/bindings", response_model=BindingOut, status_code=status.HTTP_201_CREATED)
async def accept_invite(body: BindingCreate, user_id: CurrentUserId, service: Service) -> BindingOut:
    return await service.accept_invite(user_id, body)


@router.get("/bindings", response_model=list[BindingOut])
async def list_bindings(user_id: CurrentUserId, service: Service) -> list[BindingOut]:
    return await service.list_bindings(user_id)


@router.patch("/bindings/{binding_id}", response_model=BindingOut)
async def update_binding(
    binding_id: UUID, body: BindingUpdate, user_id: CurrentUserId, service: Service
) -> BindingOut:
    return await service.update_binding(user_id, binding_id, body)


@router.post("/bindings/{binding_id}/complete-setup", response_model=BindingOut)
async def complete_setup(binding_id: UUID, user_id: CurrentUserId, service: Service) -> BindingOut:
    return await service.complete_setup(user_id, binding_id)


@router.delete("/bindings/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_binding(binding_id: UUID, user_id: CurrentUserId, service: Service) -> None:
    await service.revoke_binding(user_id, binding_id)
