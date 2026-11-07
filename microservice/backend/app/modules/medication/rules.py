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

SLOT_LABELS: dict[SlotKey, str] = {
    SlotKey.BREAKFAST_BEFORE: "早餐飯前",
    SlotKey.BREAKFAST_AFTER: "早餐飯後",
    SlotKey.LUNCH_BEFORE: "午餐飯前",
    SlotKey.LUNCH_AFTER: "午餐飯後",
    SlotKey.DINNER_BEFORE: "晚餐飯前",
    SlotKey.DINNER_AFTER: "晚餐飯後",
    SlotKey.BEDTIME: "睡前",
}

MEAL_TIMING_LABELS: dict[MealTiming, str] = {
    MealTiming.BEFORE: "飯前",
    MealTiming.AFTER: "飯後",
    MealTiming.BEDTIME: "睡前",
}

FREQUENCY_LABELS: dict[Frequency, str] = {
    Frequency.QD: "一天一次",
    Frequency.BID: "一天兩次",
    Frequency.TID: "一天三次",
    Frequency.QID: "一天四次",
    Frequency.HS: "睡前一次",
}

SAME_INGREDIENT_MESSAGE = "這兩包好像是同一種藥，請問藥師"

# 頻率 → 餐別
_MEALS_BY_FREQUENCY: dict[Frequency, tuple[str, ...]] = {
    Frequency.QD: ("breakfast",),
    Frequency.BID: ("breakfast", "dinner"),
    Frequency.TID: ("breakfast", "lunch", "dinner"),
    Frequency.QID: ("breakfast", "lunch", "dinner", "bedtime"),
    Frequency.HS: ("bedtime",),
}


# ---------- 時段與日期 ----------


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
    """還剩幾天（含今天）。還沒開始吃時為全部天數。"""
    if today < start_date:
        return days
    return max((start_date + dt.timedelta(days=days) - today).days, 0)


def is_scheduled_on(start_date: dt.date, days: int, day: dt.date) -> bool:
    """這一天在用藥期間內。"""
    return start_date <= day <= run_out_date(start_date, days)


def same_ingredient(
    new_license: str | None,
    new_ingredients: list[str],
    other_license: str | None,
    other_ingredients: list[str],
) -> bool:
    """同一張許可證，或主成分有重疊（不分大小寫）。"""
    if new_license and new_license == other_license:
        return True
    normalize = lambda items: {i.strip().lower() for i in items if i.strip()}  # noqa: E731
    return bool(normalize(new_ingredients) & normalize(other_ingredients))


def next_number(used: set[int]) -> int:
    """進行中藥品沒用到的最小正整數，讓編號維持在長輩好記的小數字。"""
    n = 1
    while n in used:
        n += 1
    return n
