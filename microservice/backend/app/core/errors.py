"""業務錯誤。service 只丟這裡的錯誤，不 import FastAPI；由 handler 轉成 HTTP 回應。

回應格式：{"error": {"code": "...", "message": "..."}}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"
    message = "請求有誤"

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        self.message = message or self.message
        self.code = code or self.code
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "資料格式不正確"


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "請重新登入"


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "沒有權限"


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "找不到資料"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "資料狀態衝突"


class TooManyRequests(AppError):
    status_code = 429
    code = "TOO_MANY_REQUESTS"
    message = "操作太頻繁，請稍後再試"


class NotImplementedYet(AppError):
    status_code = 501
    code = "NOT_IMPLEMENTED"
    message = "功能尚未實作"


def _error_body(code: str, message: str, **extra: object) -> dict:
    return {"error": {"code": code, "message": message, **extra}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content=_error_body(ValidationFailed.code, ValidationFailed.message, details=details),
        )
