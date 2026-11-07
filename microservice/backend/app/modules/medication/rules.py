"""藥區的純計算規則（規格書 §5.3）。沒有 I/O，方便寫單元測試。"""

import datetime as dt

from app.modules.medication.models import Frequency, MealTiming, SlotKey

DEFAULT_SLOT_TIMES: dict[SlotKey, dt.time] = {
    SlotKey.BREAKFAST_BEFORE: dt.time(7, 30),
    SlotKey.BREAKFAST_AFTER: dt.time(8, 0),
    SlotKey.LUNCH_BEFORE: dt.time(11, 30),
    SlotKey.LUNCH_AFTER: dt.time(12, 0),
    SlotKey.DINNER_BEFORE: dt.time(17, 30),
    SlotKey.DINNER_AFTER: dt.time(18, 0),
    SlotKey.BEDTIME: dt.time(21, 0),
}

# 頻率 → 餐別
_MEALS_BY_FREQUENCY: dict[Frequency, tuple[str, ...]] = {
    Frequency.QD: ("breakfast",),
    Frequency.BID: ("breakfast", "dinner"),
    Frequency.TID: ("breakfast", "lunch", "dinner"),
    Frequency.QID: ("breakfast", "lunch", "dinner", "bedtime"),
    Frequency.HS: ("bedtime",),
}


def allocate_slots(frequency: Frequency, meal_timing: MealTiming) -> list[SlotKey]:
    """依頻率與飯前飯後，把藥分配到時段。例如 TID + after → 三餐飯後。"""
    slots: list[SlotKey] = []
    for meal in _MEALS_BY_FREQUENCY[frequency]:
        if meal == "bedtime" or meal_timing is MealTiming.BEDTIME:
            slot = SlotKey.BEDTIME
        else:
            slot = SlotKey(f"{meal}_{meal_timing.value}")
        if slot not in slots:
            slots.append(slot)
    return slots


def run_out_date(start_date: dt.date, days: int) -> dt.date:
    """藥吃完的那一天。"""
    return start_date + dt.timedelta(days=days - 1)


def days_left(start_date: dt.date, days: int, today: dt.date) -> int:
    return max((start_date + dt.timedelta(days=days) - today).days, 0)


def next_number(used: set[int]) -> int:
    """進行中藥品沒用到的最小正整數，讓編號維持在長輩好記的小數字。"""
    n = 1
    while n in used:
        n += 1
    return n
