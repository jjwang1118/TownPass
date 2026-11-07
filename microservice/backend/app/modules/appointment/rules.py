"""回診預約的純規則與文字（UI E10～E12、E16、F08）。"""

import datetime as dt
from collections.abc import Iterable

from app.modules.appointment.models import Period

BOOKING_DAYS = 14  # 可預約未來 2 週（明天起）
DAY_BEFORE_REMIND_AT = dt.time(18, 0)  # 回診前一天幾點提醒

PERIOD_LABELS: dict[Period, str] = {
    Period.MORNING: "上午",
    Period.AFTERNOON: "下午",
    Period.EVENING: "晚上",
}
PERIOD_ORDER = {Period.MORNING: 0, Period.AFTERNOON: 1, Period.EVENING: 2}

# 每個門診的看診時間（模擬）：每 30 分鐘一個時間
SLOT_TIMES: dict[Period, list[dt.time]] = {
    Period.MORNING: [dt.time(8, 30), dt.time(9, 0), dt.time(9, 30), dt.time(10, 0), dt.time(10, 30), dt.time(11, 0)],
    Period.AFTERNOON: [dt.time(14, 0), dt.time(14, 30), dt.time(15, 0), dt.time(15, 30), dt.time(16, 0)],
    Period.EVENING: [dt.time(18, 0), dt.time(18, 30), dt.time(19, 0), dt.time(19, 30)],
}
_WEEKDAYS = "一二三四五六日"


def booking_window(today: dt.date) -> tuple[dt.date, dt.date]:
    """可預約的日期範圍：明天到 14 天後。"""
    return today + dt.timedelta(days=1), today + dt.timedelta(days=BOOKING_DAYS)


def date_label(day: dt.date) -> str:
    """11/14（五）"""
    return f"{day.month}/{day.day}（{_WEEKDAYS[day.weekday()]}）"


def time_label(period: Period, at: dt.time) -> str:
    """上午 09:30"""
    return f"{PERIOD_LABELS[period]} {at:%H:%M}"


def remaining_label(remaining: int) -> str:
    return f"還有 {remaining} 個名額" if remaining > 0 else "已額滿"


def weekly_schedule(sessions: Iterable[tuple[dt.date, Period]]) -> str:
    """醫師的門診時間：「週一、週五 上午；週二 晚上」。"""
    days_by_period: dict[Period, set[int]] = {}
    for day, period in sessions:
        days_by_period.setdefault(period, set()).add(day.weekday())
    return "；".join(
        f"{'、'.join(f'週{_WEEKDAYS[d]}' for d in sorted(days))} {PERIOD_LABELS[period]}"
        for period, days in sorted(days_by_period.items(), key=lambda kv: PERIOD_ORDER[kv[0]])
    )


def short_hospital(name: str) -> str:
    """「臺北市立聯合醫院仁愛院區」→「仁愛院區」，推播文字用。"""
    return name.removeprefix("臺北市立聯合醫院")


def reminder_where(hospital: str, department: str, doctor: str) -> str:
    """仁愛院區心臟內科林醫師"""
    return f"{short_hospital(hospital)}{department}{doctor}"


def elder_reminder(*, at: dt.time, hospital: str, department: str, doctor: str) -> tuple[str, str]:
    """UI E16：（「明天 09:30 要回診」, 「仁愛院區心臟內科林醫師，記得帶健保卡」）"""
    return f"明天 {at:%H:%M} 要回診", f"{reminder_where(hospital, department, doctor)}，記得帶健保卡"


def family_reminder(
    *, elder_name: str, at: dt.time, hospital: str, department: str, doctor: str, pronoun: str
) -> tuple[str, str]:
    """UI F08：（「王美玉 明天 09:30 要回診」, 「仁愛院區心臟內科林醫師，記得提醒或陪伴她」）"""
    return (
        f"{elder_name} 明天 {at:%H:%M} 要回診",
        f"{reminder_where(hospital, department, doctor)}，記得提醒或陪伴{pronoun}",
    )
