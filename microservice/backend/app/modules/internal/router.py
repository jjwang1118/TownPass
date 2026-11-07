import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core.config import get_settings
from app.core.deps import SessionDep
from app.core.errors import Unauthorized
from app.modules.internal.service import TickResult, TickService

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


def _verify_caller(x_internal_secret: Annotated[str | None, Header()] = None) -> None:
    # 正式版改為驗證 Cloud Scheduler 的 OIDC token
    if x_internal_secret is None or not hmac.compare_digest(x_internal_secret, get_settings().internal_secret):
        raise Unauthorized()


@router.post("/tick", response_model=TickResult, dependencies=[Depends(_verify_caller)])
async def tick(session: SessionDep) -> TickResult:
    """Cloud Scheduler 每分鐘呼叫一次（規格書 §6.1）。"""
    return await TickService(session).run()
