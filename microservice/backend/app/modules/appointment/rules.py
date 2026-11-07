"""回診預約的純規則與文字（功能規格 3-2、3-3）。"""

import datetime as dt

from app.modules.appointment.models import Period

BOOKING_DAYS = 14  # 可預約未來 2 週（明天起）
DAY_BEFORE_REMIND_AT = dt.time(18, 0)  # 前一天幾點提醒
SAME_DAY_REMIND_AT = dt.time(8, 0)  # 當天幾點提醒

PERIOD_LABELS: dict[Period, str] = {
    Period.MORNING: "上午",
    Period.AFTERNOON: "下午",
    Period.EVENING: "晚上",
}
_WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def booking_window(today: dt.date) -> tuple[dt.date, dt.date]:
    """可預約的日期範圍：明天到 14 天後。"""
    return today + dt.timedelta(days=1), today + dt.timedelta(days=BOOKING_DAYS)


def date_label(day: dt.date) -> str:
    """11/12（星期三）"""
    return f"{day.month}/{day.day}（{_WEEKDAYS[day.weekday()]}）"


def short_hospital(name: str) -> str:
    """「臺北市立聯合醫院仁愛院區」→「仁愛院區」，推播文字用。"""
    return name.removeprefix("臺北市立聯合醫院")


def appointment_reminder_text(
    *, when: str, hospital: str, department: str, doctor: str, period: Period, visit_no: int
) -> str:
    """明天上午 仁愛院區 家醫科 林醫師 回診，看診號碼 12 號"""
    return (
        f"{when}{PERIOD_LABELS[period]} {short_hospital(hospital)} {department} {doctor} 回診，"
        f"看診號碼 {visit_no} 號"
    )
