"""救護人員查詢次數限制，避免猜卡號。

只記在這台伺服器的記憶體裡；Render 免費方案只有一台，比賽規模足夠。
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from uuid import UUID


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self._hits: dict[UUID, deque[float]] = defaultdict(deque)

    def allow(self, key: UUID) -> bool:
        now = self.clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


# 每位救護人員每分鐘最多查詢 10 次
lookup_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)
