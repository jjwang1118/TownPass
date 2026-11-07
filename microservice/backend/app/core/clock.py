from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

# 資料庫一律存 UTC；業務邏輯（時段、日期）以台北時間計算。
TAIPEI = ZoneInfo("Asia/Taipei")


def now() -> datetime:
    return datetime.now(UTC)


def today_taipei() -> date:
    return now().astimezone(TAIPEI).date()
