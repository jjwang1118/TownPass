import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core.config import get_settings
from app.core.deps import SessionDep
from app.core.errors import Unauthorized
from app.modules.internal.service import TickResult, TickService

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


def _verify_caller(x_internal_secret: Annotated[str | None, Header()] = None) -> None:
    # 本地部署由後端內建排程觸發；這個 API 留給手動測試或外部排程使用
    if x_internal_secret is None or not hmac.compare_digest(x_internal_secret, get_settings().internal_secret):
        raise Unauthorized()


@router.post("/tick", response_model=TickResult, dependencies=[Depends(_verify_caller)])
async def tick(session: SessionDep) -> TickResult:
    """手動執行一次排程（規格書 §6.1）。平常由後端內建排程每分鐘執行。"""
    return await TickService(session).run()
