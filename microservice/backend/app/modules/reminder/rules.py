"""吃藥提醒的純規則與文字（功能規格 1-5、1-6、3-1）。"""

import datetime as dt

from app.modules.medication.models import SlotKey

MAX_ATTEMPTS = 3  # 推播長輩幾次後，通知家人沒有回應
LATE_WINDOW = dt.timedelta(minutes=30)  # 排程延誤時，超過時段多久就不再補發
REFILL_DAYS_BEFORE = 7  # 藥吃完前幾天提醒回診
REFILL_SEND_AT = dt.time(9, 0)  # 每天幾點發回診提醒

MEAL_WORD: dict[SlotKey, str] = {  # 朗讀稿用
    SlotKey.BREAKFAST_BEFORE: "飯前",
    SlotKey.LUNCH_BEFORE: "飯前",
    SlotKey.DINNER_BEFORE: "飯前",
    SlotKey.BREAKFAST_AFTER: "飯後",
    SlotKey.LUNCH_AFTER: "飯後",
    SlotKey.DINNER_AFTER: "飯後",
    SlotKey.BEDTIME: "睡前",
}


def hhmm(at: dt.datetime, tz: dt.tzinfo) -> str:
    return at.astimezone(tz).strftime("%H:%M")


def pronoun(gender: str | None) -> str:
    return {"female": "她", "male": "他"}.get(gender or "", "他")


def no_response_text(relation_label: str, time_text: str, gender: str | None) -> str:
    """功能規格 1-6：「媽媽 18:00 的吃藥提醒沒有回應，要不要打給她？」"""
    return f"{relation_label} {time_text} 的吃藥提醒沒有回應，要不要打給{pronoun(gender)}？"


def acked_text(relation_label: str, time_text: str) -> str:
    """長輩按「好，我知道了」不代表已經吃藥，所以寫「已回應」。"""
    return f"{relation_label}已回應 {time_text} 的吃藥提醒"


def refill_text(numbers: list[int], days: int = REFILL_DAYS_BEFORE) -> str:
    """功能規格 3-1：「1 號、3 號的藥再 7 天就吃完囉，要記得回診或領慢箋」"""
    listed = "、".join(f"{n} 號" for n in sorted(numbers))
    return f"{listed}的藥再 {days} 天就吃完囉，要記得回診或領慢箋"


def nudge_text(family_name: str) -> str:
    return f"{family_name}提醒你吃藥喔"
