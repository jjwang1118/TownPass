"""朗讀稿：把結構化資料套進各語言的模板，交給手機 TTS 念。

用模板產生，不經過翻譯 AI，所以內容固定、可離線。目前有國語（zh）與英文（en）；
英文版的科別、用途、稱呼用 glossary.py 的對照表翻成原本的意思，查不到就不念。
之後加台語時，在這裡補模板即可，呼叫端不用改。
"""

import datetime as dt
import re
from decimal import Decimal
from enum import StrEnum

from app.modules.speech import glossary


class Lang(StrEnum):
    ZH = "zh"
    EN = "en"


_CJK = re.compile(r"[㐀-鿿豈-﫿]")
_CJK_RUN = re.compile(r"[㐀-鿿豈-﫿　-〿＀-￯（）]+")


def _ensure_supported(lang: Lang) -> None:
    if lang not in (Lang.ZH, Lang.EN):
        raise NotImplementedError(f"朗讀稿尚未支援 {lang}")


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def without_latin(text: str) -> str:
    """去掉英文字母（中文稿的科別、用途、稱呼用；藥名改用 drug_name）。"""
    return re.sub(r"\s+", " ", re.sub(r"[A-Za-z]+", "", text)).strip(" ，,")


def without_cjk(text: str) -> str:
    """去掉中文字與全形符號，留下英文部分（英文稿用）。"""
    return re.sub(r"\s+", " ", _CJK_RUN.sub(" ", text)).strip(" ,.;:-")


# ---------- 藥名 ----------


def drug_name(name: str, name_zh: str | None = None) -> str:
    """中文稿要念的藥名：有中文名就只念中文名，只有英文名就照原文念。

    依序找含中文的名稱：食藥署許可證的中文品名 → 藥袋上的藥名；都沒有中文就念藥袋上的原文。
    """
    for candidate in (name_zh, name):
        if candidate and has_cjk(candidate):
            return candidate.strip()
    return name.strip()


def drug_name_en(name: str, name_en: str | None = None) -> str:
    """英文稿要念的藥名：藥袋上的英文名 → 食藥署許可證的英文品名；都沒有英文就不念。"""
    for candidate in (name, name_en):
        if candidate and (english := without_cjk(candidate)) and re.search(r"[A-Za-z]", english):
            return english
    return ""


# ---------- 英文稿的翻譯（對照表） ----------


def _lookup(text: str, table: dict[str, str]) -> str:
    """先查對照表；查不到但本身有英文就用英文部分；都沒有就回傳空字串（不念）。"""
    if (hit := table.get(without_latin(text))) is not None:
        return hit
    english = without_cjk(text)
    return english if re.search(r"[A-Za-z]", english) else ""


def department_en(department: str) -> str:
    """家醫科 → Family Medicine。"""
    return _lookup(department, glossary.DEPARTMENTS)


def purpose_en(purpose: str) -> str:
    """降血壓 → blood pressure（句子念成 for blood pressure）。"""
    return _lookup(purpose, glossary.PURPOSES)


def title_en(title: str) -> str:
    """陳阿嬤 → Grandma Chen；王先生 → Mr. Wang；阿公 → Grandpa；查不到稱呼就不念。"""
    text = without_latin(title).replace(" ", "")
    for zh, en in glossary.KINSHIP:
        if zh in text:
            surname = glossary.SURNAMES.get(text[0]) if text[0] != zh[0] else None
            if not surname or en in ("Mom", "Dad"):
                return en
            return f"{en} {surname}"
    english = without_cjk(title)
    return english if re.search(r"[A-Za-z]", english) else ""


def meal_en(meal_word: str) -> str:
    """飯後 → after meals。"""
    return glossary.MEAL.get(meal_word, "")


# ---------- 時間、顆數 ----------


def speak_time(t: dt.time, lang: Lang = Lang.ZH) -> str:
    """zh：08:00 → 早上 8 點；13:30 → 下午 1 點半。en：8 AM；1:30 PM。"""
    _ensure_supported(lang)
    h, m = t.hour, t.minute
    if lang is Lang.EN:
        hour12 = h % 12 or 12
        suffix = "AM" if h < 12 else "PM"
        return f"{hour12} {suffix}" if m == 0 else f"{hour12}:{m:02d} {suffix}"
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
    """zh：1 → 1 顆；0.5 → 半顆；1.5 → 1 顆半。en：1 tablet；half a tablet；1 and a half tablets。"""
    _ensure_supported(lang)
    whole = int(qty)
    fraction = qty - whole
    half = fraction == Decimal("0.5")
    if lang is Lang.EN:
        if fraction == 0:
            return f"{whole} tablet" if whole == 1 else f"{whole} tablets"
        if half:
            return "half a tablet" if whole == 0 else f"{whole} and a half tablets"
        return f"{qty.normalize()} tablets"
    if fraction == 0:
        return f"{whole} 顆"
    if half:
        return "半顆" if whole == 0 else f"{whole} 顆半"
    return f"{qty.normalize()} 顆"


def _join_en(items: list[str]) -> str:
    """[a] → a；[a, b] → a and b；[a, b, c] → a, b and c。"""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


# ---------- 朗讀稿 ----------


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
    """藥卡「念給我聽」。drug 為該語言的藥名（drug_name() 或 drug_name_en() 的結果）；
    department、purpose、meal_label 傳中文原文，英文稿會自己查對照表。

    zh：1 號藥，脈優錠，家醫科開的，降血壓。一次 1 顆，飯後吃，早上 8 點、晚上 6 點。還剩 20 天。
    en：Medicine number 1, Amlodipine 5mg, from Family Medicine, for blood pressure.
        Take 1 tablet after meals, at 8 AM and 6 PM. 20 days left.
    """
    _ensure_supported(lang)
    if lang is Lang.EN:
        parts = [f"Medicine number {number}"]
        if drug:
            parts.append(drug)
        if dept := department_en(department):
            parts.append(f"from {dept}")
        if use := purpose_en(purpose):
            parts.append(f"for {use}")
        when = _join_en([speak_time(t, lang) for t in sorted(times)])
        meal = meal_en(meal_label)
        take = f"Take {qty_text(dose_qty, lang)}" + (f" {meal}" if meal else "")
        if days_left > 1:
            tail = f"{days_left} days left."
        elif days_left == 1:
            tail = "1 day left."
        else:
            tail = "All finished."
        return f"{', '.join(parts)}. {take}, at {when}. {tail}"

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
    """吃藥提醒（功能規格 1-5）。items 為（編號, 該語言的藥名, 顆數）；title、meal_word 傳中文原文。

    zh：陳阿嬤，吃藥時間到囉～飯後吃：1 號 脈優錠 2 顆、3 號 Metformin 500mg 1 顆
    en：Grandma Chen, it's time for your medicine. After meals: number 1, Amlodipine 5mg, 2 tablets;
        number 3, Metformin 500mg, 1 tablet.
    """
    _ensure_supported(lang)
    if lang is Lang.EN:
        doses = "; ".join(
            ", ".join(p for p in (f"number {number}", drug, qty_text(qty, lang)) if p) for number, drug, qty in items
        )
        name = title_en(title)
        head = f"{name}, it's time for your medicine." if name else "It's time for your medicine."
        meal = meal_en(meal_word)
        return f"{head} {meal[0].upper() + meal[1:]}: {doses}." if meal else f"{head} {doses}."

    doses = "、".join(
        " ".join(p for p in (f"{number} 號", drug, qty_text(qty, lang)) if p) for number, drug, qty in items
    )
    head = f"{t}，" if (t := without_latin(title)) else ""
    return f"{head}吃藥時間到囉～{meal_word}吃：{doses}"


def slot(
    *,
    time: dt.time,
    groups: list[tuple[str, str, list[tuple[int, Decimal]]]],
    lang: Lang = Lang.ZH,
) -> str:
    """時段「唸給我聽」與吃藥提醒（UI E02、E03）。groups 為（藥單字母, 科別, [(序號, 顆數)]），依藥單分組。

    中文稿不念英文字母（交付規格），所以用科別區分藥單；沒有科別時念「另一包藥」。藥名不念。
    zh：中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆
    en：12 PM medicine: Endocrinology, number 1, 1 tablet; number 2, 1 tablet.
    """
    _ensure_supported(lang)
    if lang is Lang.EN:
        parts = []
        for letter, department, items in groups:
            doses = "; ".join(f"number {seq}, {qty_text(qty, lang)}" for seq, qty in items)
            parts.append(f"{department_en(department) or f'Bag {letter}'}, {doses}")
        return f"{speak_time(time, lang)} medicine: {'. '.join(parts)}."

    parts = []
    for _, department, items in groups:
        doses = "、".join(f"{seq} 號 {qty_text(qty, lang)}" for seq, qty in items)
        parts.append(f"{without_latin(department) or '另一包藥'} {doses}")
    return f"{speak_time(time, lang)}，要吃{'；'.join(parts)}"
