"""JWT、密碼雜湊、欄位加密。"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core import clock
from app.core.config import get_settings
from app.core.errors import Unauthorized

# ---------- JWT ----------


class TokenKind(StrEnum):
    USER = "user"  # 長輩、家人（台北通登入）
    RESPONDER = "responder"  # 救護人員（消防局帳號）


@dataclass(frozen=True)
class TokenClaims:
    subject: UUID
    kind: TokenKind
    expires_at: datetime


def issue_token(subject: UUID, kind: TokenKind) -> tuple[str, datetime]:
    settings = get_settings()
    hours = settings.responder_token_ttl_hours if kind is TokenKind.RESPONDER else settings.user_token_ttl_hours
    expires_at = clock.now() + timedelta(hours=hours)
    token = jwt.encode(
        {"sub": str(subject), "kind": kind.value, "exp": expires_at},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_token(token: str) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims(
            subject=UUID(payload["sub"]),
            kind=TokenKind(payload["kind"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Unauthorized() from exc


# ---------- 密碼 ----------

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# ---------- 欄位加密（個資法第 6 條特種個資、電話）----------


@lru_cache
def _fernet() -> Fernet:
    key = get_settings().field_encryption_key
    if not key:
        raise RuntimeError("未設定 FIELD_ENCRYPTION_KEY，無法加解密個資欄位")
    return Fernet(key.encode())


class EncryptedText(TypeDecorator[str]):
    """寫入時加密、讀出時解密的字串欄位。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        return None if value is None else _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        return None if value is None else _fernet().decrypt(value.encode()).decode()


class EncryptedJSON(TypeDecorator[Any]):
    """寫入時轉 JSON 再加密的欄位，用於慢性病、過敏清單。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        raw = json.dumps(value, ensure_ascii=False)
        return _fernet().encrypt(raw.encode()).decode()

    def process_result_value(self, value: str | None, dialect: Any) -> Any:
        return None if value is None else json.loads(_fernet().decrypt(value.encode()))
