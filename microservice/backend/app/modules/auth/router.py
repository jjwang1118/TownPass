from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUserId, SessionDep
from app.integrations.townpass.messages import UserinfoReply
from app.modules.auth.schemas import MeOut, RoleIn, TokenOut
from app.modules.auth.service import AuthService

router = APIRouter(tags=["auth"])


def get_service(session: SessionDep) -> AuthService:
    return AuthService(session)


Service = Annotated[AuthService, Depends(get_service)]


@router.post("/auth/townpass", response_model=TokenOut)
async def login_with_townpass(body: UserinfoReply, service: Service) -> TokenOut:
    """body 為 App 對 { name: 'userinfo' } 的回覆，前端 JSON.parse 後原封不動送來。"""
    return await service.login_with_townpass(body.data)


@router.put("/me/role", response_model=MeOut)
async def set_role(body: RoleIn, user_id: CurrentUserId, service: Service) -> MeOut:
    return await service.set_role(user_id, body.role)


@router.get("/me", response_model=MeOut)
async def get_me(user_id: CurrentUserId, service: Service) -> MeOut:
    return await service.get_me(user_id)
