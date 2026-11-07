"""吃藥提醒的純規則與文字（UI E09、F04、功能規格 3-1）。"""

import datetime as dt

LATE_WINDOW = dt.timedelta(minutes=30)  # 排程延誤時，超過時段多久就不再補發
REFILL_DAYS_BEFORE = 7  # 藥吃完前幾天提醒回診
REFILL_SEND_AT = dt.time(9, 0)  # 每天幾點發回診提醒


def pronoun(gender: str | None) -> str:
    return {"female": "她", "male": "他"}.get(gender or "", "他")


def elder_title(label: str, at: dt.time) -> str:
    """長輩收到的推播標題：「中午 12:00 該吃藥了」"""
    return f"{label} {at:%H:%M} 該吃藥了"


def elder_body(doses: str) -> str:
    """「B1、B2 各 1 顆，點開可以聽語音」"""
    return f"{doses}，點開可以聽語音"


def family_title(elder_name: str, label: str, at: dt.time) -> str:
    """家屬收到的推播標題：「王美玉 中午 12:00 該吃藥了」（和長輩同時間）"""
    return f"{elder_name} {label} {at:%H:%M} 該吃藥了"


def family_body(doses: str, gender: str | None) -> str:
    """「B1、B2 各 1 顆，記得關心她」"""
    return f"{doses}，記得關心{pronoun(gender)}"


def refill_text(prescriptions: list[tuple[str, str | None, str | None]], days: int = REFILL_DAYS_BEFORE) -> str:
    """功能規格 3-1：「藥單 A（仁愛院區 心臟內科）再 7 天就吃完囉，要記得回診或領慢箋」。

    prescriptions 為（字母, 院區, 科別）。
    """
    listed = "、".join(
        f"藥單 {letter}（{where}）" if (where := " ".join(x for x in (_short(hospital), department) if x)) else f"藥單 {letter}"
        for letter, hospital, department in prescriptions
    )
    return f"{listed}再 {days} 天就吃完囉，要記得回診或領慢箋"


def nudge_text(family_name: str) -> str:
    return f"{family_name}提醒你吃藥喔"


def _short(hospital: str | None) -> str:
    return (hospital or "").removeprefix("臺北市立聯合醫院")
