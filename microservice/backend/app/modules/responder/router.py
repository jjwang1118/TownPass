from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import ResponderClaims, SessionDep
from app.modules.emergency_card.schemas import ResponderCardOut
from app.modules.responder.schemas import LoginIn, LookupIn, ResponderTokenOut, UnitsOut
from app.modules.responder.service import ResponderService

router = APIRouter(prefix="/responder", tags=["responder"])


def get_service(session: SessionDep) -> ResponderService:
    return ResponderService(session)


Service = Annotated[ResponderService, Depends(get_service)]


@router.get("/units", response_model=UnitsOut)
async def units() -> UnitsOut:
    """所屬單位清單（不需登入）。"""
    return ResponderService.units()


@router.post("/login", response_model=ResponderTokenOut)
async def login(body: LoginIn, service: Service) -> ResponderTokenOut:
    return await service.login(body)


@router.post("/cards/lookup", response_model=ResponderCardOut)
async def lookup_card(body: LookupIn, claims: ResponderClaims, service: Service) -> ResponderCardOut:
    return await service.lookup_card(claims.subject, body)
