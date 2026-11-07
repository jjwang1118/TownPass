import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401  確保所有 ORM 模型都已載入
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.modules.appointment.router import router as appointment_router
from app.modules.auth.router import router as auth_router
from app.modules.demo.router import router as demo_router
from app.modules.emergency_card.router import router as emergency_card_router
from app.modules.family.router import router as family_router
from app.modules.internal import scheduler
from app.modules.internal.router import router as internal_router
from app.modules.medication.router import router as medication_router
from app.modules.notification.router import router as notification_router
from app.modules.reminder.router import router as reminder_router
from app.modules.responder.router import router as responder_router

API_PREFIX = "/api/v1"

# 讓 app.* 的 INFO log（排程結果、推播內容）顯示在終端機
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(scheduler.run_forever()) if get_settings().scheduler_enabled else None
    yield
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="呷藥囉 API", version="0.1.0", lifespan=lifespan)

    # 微服務網頁在台北通的 WebView 中呼叫後端，需要 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    for router in (
        auth_router,
        family_router,
        medication_router,
        reminder_router,
        emergency_card_router,
        responder_router,
        appointment_router,
        notification_router,
        internal_router,
    ):
        api.include_router(router)
    if settings.demo_mode:
        api.include_router(demo_router)
    app.include_router(api)

    # 健康檢查
    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
