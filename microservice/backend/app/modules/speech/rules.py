"""朗讀稿：把結構化資料套進各語言的模板，交給手機 TTS 念。

用模板產生，不經過翻譯，所以內容固定、可離線。目前只有國語（zh）；
之後加英文、台語時，在這裡補模板即可，呼叫端不用改。
"""

import datetime as dt
import re
from decimal import Decimal
from enum import StrEnum


class Lang(StrEnum):
    ZH = "zh"


_CJK = re.compile(r"[㐀-鿿豈-﫿]")


def _ensure_supported(lang: Lang) -> None:
    if lang is not Lang.ZH:
        raise NotImplementedError(f"朗讀稿尚未支援 {lang}")


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def without_latin(text: str) -> str:
    """去掉英文字母（科別、用途、稱呼用；藥名改用 drug_name）。"""
    return re.sub(r"\s+", " ", re.sub(r"[A-Za-z]+", "", text)).strip(" ，,")


def drug_name(name: str, name_zh: str | None = None) -> str:
    """要念的藥名：有中文名就只念中文名，只有英文名就照原文念。

    依序找含中文的名稱：食藥署許可證的中文品名 → 藥袋上的藥名；都沒有中文就念藥袋上的原文。
    """
    for candidate in (name_zh, name):
        if candidate and has_cjk(candidate):
            return candidate.strip()
    return name.strip()


def speak_time(t: dt.time, lang: Lang = Lang.ZH) -> str:
    """08:00 → 早上 8 點；13:30 → 下午 1 點半。"""
    _ensure_supported(lang)
    h, m = t.hour, t.minute
    if h < 5:
        period, hour = "凌晨", h
    elif h < 11:
        period, hour = "早上", h
    elif h == 11:
        period, hour = "上午", h
    elif h == 12:
        period, hour = "中午", h
    elif h < 18:
        period, hour = "下午", h - 12
    else:
        period, hour = "晚上", h - 12
    if m == 0:
        minute = ""
    elif m == 30:
        minute = "半"
    else:
        minute = f" {m} 分"
    return f"{period} {hour} 點{minute}"


def qty_text(qty: Decimal, lang: Lang = Lang.ZH) -> str:
    """1 → 1 顆；0.5 → 半顆；1.5 → 1 顆半。"""
    _ensure_supported(lang)
    whole = int(qty)
    fraction = qty - whole
    if fraction == 0:
        return f"{whole} 顆"
    if fraction == Decimal("0.5"):
        return "半顆" if whole == 0 else f"{whole} 顆半"
    return f"{qty.normalize()} 顆"


def medication_card(
    *,
    number: int,
    drug: str,
    department: str,
    purpose: str,
    dose_qty: Decimal,
    meal_label: str,
    times: list[dt.time],
    days_left: int,
    lang: Lang = Lang.ZH,
) -> str:
    """藥卡「念給我聽」。drug 為 drug_name() 的結果。

    例：1 號藥，脈優錠，家醫科開的，降血壓。一次 1 顆，飯後吃，早上 8 點、晚上 6 點。還剩 20 天。
    """
    _ensure_supported(lang)
    parts = [f"{number} 號藥"]
    if drug:
        parts.append(drug)
    if department := without_latin(department):
        parts.append(f"{department}開的")
    head = "，".join(parts)
    if purpose := without_latin(purpose):
        head += f"，{purpose}"
    when = "、".join(speak_time(t, lang) for t in sorted(times))
    body = f"一次 {qty_text(dose_qty, lang)}，{meal_label}吃，{when}"
    tail = f"還剩 {days_left} 天" if days_left > 0 else "已經吃完了"
    return f"{head}。{body}。{tail}。"


def reminder(
    *,
    title: str,
    meal_word: str,
    items: list[tuple[int, str, Decimal]],
    lang: Lang = Lang.ZH,
) -> str:
    """吃藥提醒（功能規格 1-5）。items 為（編號, drug_name() 的結果, 顆數）。

    例：陳阿嬤，吃藥時間到囉～飯後吃：1 號 脈優錠 2 顆、3 號 Metformin 500mg 1 顆
    """
    _ensure_supported(lang)
    doses = "、".join(
        " ".join(p for p in (f"{number} 號", drug, qty_text(qty, lang)) if p) for number, drug, qty in items
    )
    head = f"{t}，" if (t := without_latin(title)) else ""
    return f"{head}吃藥時間到囉～{meal_word}吃：{doses}"
