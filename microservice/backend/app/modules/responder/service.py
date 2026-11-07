from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotImplementedYet
from app.modules.emergency_card.schemas import ResponderCardOut
from app.modules.responder.repository import ResponderRepository
from app.modules.responder.schemas import LoginIn, LookupIn, ResponderTokenOut


class ResponderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ResponderRepository(session)

    async def login(self, body: LoginIn) -> ResponderTokenOut:
        """比對名冊：在職且有救護權限才發 token，否則 403 RESPONDER_NOT_AUTHORIZED。"""
        raise NotImplementedYet()

    async def ensure_authorized(self, responder_id: UUID) -> None:
        """每次請求重新確認名冊狀態，離職立即失效。"""
        raise NotImplementedYet()

    async def lookup_card(self, responder_id: UUID, body: LookupIn) -> ResponderCardOut:
        """qr → rules.code_from_qr、method=qr；code → rules.normalize_code、method=manual。
        再呼叫 EmergencyCardService.lookup_for_responder。每人每分鐘最多 10 次。"""
        raise NotImplementedYet()
