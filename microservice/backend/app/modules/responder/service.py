from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, TooManyRequests, Unauthorized, ValidationFailed
from app.core.security import TokenKind, issue_token, verify_password
from app.modules.emergency_card import rules as card_rules
from app.modules.emergency_card.models import AccessMethod
from app.modules.emergency_card.schemas import ResponderCardOut
from app.modules.emergency_card.service import EmergencyCardService, ResponderInfo
from app.modules.responder.models import EmploymentStatus, Responder
from app.modules.responder.rate_limit import lookup_limiter
from app.modules.responder.repository import ResponderRepository
from app.modules.responder.schemas import LoginIn, LookupIn, ResponderTokenOut


class ResponderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ResponderRepository(session)

    async def login(self, body: LoginIn) -> ResponderTokenOut:
        """比對消防局名冊：在職且有救護權限才發 token（12 小時，一個勤務班）。"""
        responder = await self.repo.get_by_account(body.account.strip().upper())
        if responder is None or not verify_password(responder.password_hash, body.password):
            # 帳號不存在和密碼錯誤回同樣的訊息，避免被試出有哪些帳號
            raise Unauthorized("帳號或密碼錯誤", code="INVALID_CREDENTIALS")
        self._check_roster(responder)

        token, expires_at = issue_token(responder.id, TokenKind.RESPONDER)
        return ResponderTokenOut(
            access_token=token,
            expires_at=expires_at,
            name=responder.name,
            unit=responder.unit,
            title=responder.title,
        )

    async def ensure_authorized(self, responder_id: UUID) -> Responder:
        """每次請求重新確認名冊，登入後才離職或被取消權限也會立即失效。"""
        responder = await self.repo.get(responder_id)
        if responder is None:
            raise Unauthorized()
        self._check_roster(responder)
        return responder

    async def lookup_card(self, responder_id: UUID, body: LookupIn) -> ResponderCardOut:
        responder = await self.ensure_authorized(responder_id)
        if not lookup_limiter.allow(responder.id):
            raise TooManyRequests("查詢太頻繁，請稍後再試", code="RATE_LIMITED")

        if body.qr is not None and body.qr.data is not None:
            # 救命卡 QR 是網址；也接受 QR 裡直接是卡號
            code = card_rules.code_from_qr(body.qr.data) or card_rules.normalize_code(body.qr.data)
            method = AccessMethod.QR
        else:
            code = card_rules.normalize_code(body.code or "")
            method = AccessMethod.MANUAL
        if code is None:
            raise ValidationFailed("這不是救命卡的 QR Code 或卡號", code="CARD_CODE_INVALID")

        position = body.location.data if body.location is not None else None
        return await EmergencyCardService(self.session).lookup_for_responder(
            ResponderInfo(id=responder.id, name=responder.name, unit=responder.unit, unit_phone=responder.unit_phone),
            code,
            method,
            latitude=Decimal(str(round(position.latitude, 6))) if position else None,
            longitude=Decimal(str(round(position.longitude, 6))) if position else None,
        )

    @staticmethod
    def _check_roster(responder: Responder) -> None:
        if responder.employment_status is not EmploymentStatus.ACTIVE or not responder.has_ems_permission:
            raise Forbidden("無權限", code="RESPONDER_NOT_AUTHORIZED")
