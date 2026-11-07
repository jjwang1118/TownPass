"""共用的 FastAPI Depends：資料庫 session、目前登入者。"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Unauthorized
from app.core.security import TokenClaims, TokenKind, decode_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


def _claims(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> TokenClaims:
    if credentials is None:
        raise Unauthorized()
    return decode_token(credentials.credentials)


def _current_user_id(claims: Annotated[TokenClaims, Depends(_claims)]) -> UUID:
    if claims.kind is not TokenKind.USER:
        raise Unauthorized()
    return claims.subject


def _current_responder_claims(claims: Annotated[TokenClaims, Depends(_claims)]) -> TokenClaims:
    if claims.kind is not TokenKind.RESPONDER:
        raise Unauthorized()
    return claims


# 長輩或家人（台北通登入）的 users.id
CurrentUserId = Annotated[UUID, Depends(_current_user_id)]

# 救護人員的 token；名冊狀態由 responder 模組在每次請求時再確認
ResponderClaims = Annotated[TokenClaims, Depends(_current_responder_claims)]
