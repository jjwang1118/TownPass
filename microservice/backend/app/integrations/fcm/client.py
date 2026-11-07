"""推播發送。沒有設定 FIREBASE_CREDENTIALS 時只寫 log，方便本機開發。"""

import asyncio
import json
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
    def __init__(self, credentials: str) -> None:
        import firebase_admin
        from firebase_admin import credentials as fb_credentials

        if not firebase_admin._apps:
            # 直接貼上的 JSON 內容（Render 環境變數），或 JSON 檔路徑（Render Secret File、本機）
            source = json.loads(credentials) if credentials.lstrip().startswith("{") else credentials
            firebase_admin.initialize_app(fb_credentials.Certificate(source))

    async def send(self, tokens: list[str], message: PushMessage) -> None:
        from firebase_admin import messaging

        multicast = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(title=message.title, body=message.body),
            data=message.data,
        )
        # firebase-admin 是同步 API，放到背景執行緒，避免卡住其他請求
        response = await asyncio.to_thread(messaging.send_each_for_multicast, multicast)
        if response.failure_count:
            logger.warning("[push] %d/%d 則失敗", response.failure_count, len(tokens))


@lru_cache
def get_pusher() -> Pusher:
    """FIREBASE_CREDENTIALS：空白＝只寫 log；否則為服務帳戶金鑰（JSON 內容或檔案路徑）。"""
    credentials = get_settings().firebase_credentials
    return FcmPusher(credentials) if credentials else LogPusher()
