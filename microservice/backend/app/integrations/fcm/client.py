"""推播發送。沒有設定 FIREBASE_CREDENTIALS 時只寫 log，方便本機開發。"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushMessage:
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


class Pusher(Protocol):
    async def send(self, tokens: list[str], message: PushMessage) -> None: ...


class LogPusher:
    async def send(self, tokens: list[str], message: PushMessage) -> None:
        logger.info("[push] to=%d title=%s body=%s data=%s", len(tokens), message.title, message.body, message.data)


class FcmPusher:
    def __init__(self, credentials_path: str) -> None:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(credentials_path))

    async def send(self, tokens: list[str], message: PushMessage) -> None:
        from firebase_admin import messaging

        # firebase-admin 為同步 API；之後量大時改用 asyncio.to_thread
        messaging.send_each_for_multicast(
            messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(title=message.title, body=message.body),
                data=message.data,
            )
        )


@lru_cache
def get_pusher() -> Pusher:
    credentials_path = get_settings().firebase_credentials
    return FcmPusher(credentials_path) if credentials_path else LogPusher()
