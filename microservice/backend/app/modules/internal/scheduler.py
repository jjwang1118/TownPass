"""後端內建排程：每分鐘執行一次 TickService（吃藥提醒、沒回應通知、回診與預約提醒）。

本地部署沒有外部排程服務，所以由後端自己每分鐘觸發。設定 SCHEDULER_ENABLED=false 可關閉，
改由外部呼叫 POST /api/v1/internal/tick。
"""

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.db import SessionLocal
from app.modules.internal.service import TickResult, TickService

logger = logging.getLogger(__name__)


async def tick_once(session_factory: Callable[[], AsyncSession] = SessionLocal) -> TickResult:
    async with session_factory() as session:
        result = await TickService(session).run()
    if any(result.model_dump().values()):
        logger.info("[排程] %s", result.model_dump())
    return result


def seconds_until_next_minute() -> float:
    """對齊到下一分鐘的第 1 秒，讓 08:00 的提醒在 08:00:01 左右送出。"""
    now = clock.now()
    return 61 - now.second - now.microsecond / 1_000_000


async def run_forever() -> None:
    logger.info("[排程] 已啟動，每分鐘執行一次")
    while True:
        await asyncio.sleep(seconds_until_next_minute())
        try:
            await tick_once()
        except Exception:  # 單次失敗（例如資料庫暫時連不上）不影響下一分鐘
            logger.exception("[排程] 執行失敗")
