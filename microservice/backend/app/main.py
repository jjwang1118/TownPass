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
from app.modules.internal.router import router as internal_router
from app.modules.medication.router import router as medication_router
from app.modules.notification.router import router as notification_router
from app.modules.reminder.router import router as reminder_router
from app.modules.responder.router import router as responder_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.on_cloud and (problems := settings.production_problems()):
        # 在雲端用到開發設定時直接啟動失敗；Render 會保留舊版本繼續服務
        raise RuntimeError("部署設定有誤：" + "；".join(problems))

    app = FastAPI(title="呷藥囉 API", version="0.1.0")

    # 微服務網頁（Firebase Hosting）在 WebView 中呼叫後端（Render），需要 CORS
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

    # 健康檢查（部分平台保留結尾為 z 的路徑，如 /healthz，所以用 /health）
    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
