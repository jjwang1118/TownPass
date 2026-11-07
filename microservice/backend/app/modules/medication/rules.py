"""藥區的純計算規則（規格書 §5.3）。沒有 I/O，方便寫單元測試。"""

import datetime as dt
import difflib
import re
import string
from collections.abc import Iterable
from decimal import Decimal

from app.integrations.fda.importer import normalize
from app.modules.medication.models import Frequency, MealTiming, SlotKey

# 固定四個時段，不能修改
SLOT_TIMES: dict[SlotKey, dt.time] = {
    SlotKey.MORNING: dt.time(9, 0),
    SlotKey.NOON: dt.time(12, 0),
    SlotKey.EVENING: dt.time(18, 0),
    SlotKey.BEDTIME: dt.time(22, 0),
}
SLOT_ORDER = list(SLOT_TIMES)

SLOT_LABELS: dict[SlotKey, str] = {
    SlotKey.MORNING: "早上",
    SlotKey.NOON: "中午",
    SlotKey.EVENING: "晚上",
    SlotKey.BEDTIME: "睡前",
}

MEAL_TIMING_LABELS: dict[MealTiming, str] = {
    MealTiming.BEFORE: "飯前",
    MealTiming.AFTER: "飯後",
}

# 藥袋 QR、拍照辨識給的是頻率時，換成時段
FREQUENCY_SLOTS: dict[Frequency, list[SlotKey]] = {
    Frequency.QD: [SlotKey.MORNING],
    Frequency.BID: [SlotKey.MORNING, SlotKey.EVENING],
    Frequency.TID: [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING],
    Frequency.QID: [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING, SlotKey.BEDTIME],
    Frequency.HS: [SlotKey.BEDTIME],
}

SAME_INGREDIENT_MESSAGE = "這兩包好像是同一種藥，請問藥師"
LETTERS = string.ascii_uppercase

# 拍照辨識：信心分數低於這個值，畫面用紅框標示「電腦不確定」
CONFIDENCE_THRESHOLD = 0.8
# 藥名比對：相似度低於這個值就當作找不到（不帶入藥品代號，避免拿錯的藥比對同成分）
NAME_MATCH_MIN = 0.75

# 「北市聯醫常用藥」（模擬，依 ATC 碼）：藥名搜尋排前面
COMMON_ATC = frozenset(
    {
        "C08CA01",  # amlodipine
        "B01AC06",  # aspirin
        "C10AA05",  # atorvastatin
        "C10AA07",  # rosuvastatin
        "A10BA02",  # metformin
        "A10BH05",  # linagliptin
        "A10BB12",  # glimepiride
        "C09CA01",  # losartan
        "C09CA03",  # valsartan
        "C07AB07",  # bisoprolol
        "N02BE01",  # acetaminophen
        "A02BC01",  # omeprazole
    }
)
# 口服劑型排在注射、外用前面
ORAL_FORM_HINTS = ("錠", "膠囊", "內服", "糖漿", "顆粒")


# ---------- 時段與日期 ----------


def sort_slots(slots: Iterable[SlotKey | str]) -> list[SlotKey]:
    """去除重複，依時間排序。"""
    unique = {SlotKey(s) for s in slots}
    return [s for s in SLOT_ORDER if s in unique]


def run_out_date(visit_date: dt.date, days: int) -> dt.date:
    """藥吃完的那一天。"""
    return visit_date + dt.timedelta(days=days - 1)


def days_left(visit_date: dt.date, days: int, today: dt.date) -> int:
    """還剩幾天（含今天）。還沒開始吃時為全部天數。"""
    if today < visit_date:
        return days
    return max((visit_date + dt.timedelta(days=days) - today).days, 0)


def is_scheduled_on(visit_date: dt.date, days: int, day: dt.date) -> bool:
    """這一天在用藥期間內。"""
    return visit_date <= day <= run_out_date(visit_date, days)


# ---------- 藥量（和前端 utils/supply.ts 相同）----------
#
# 還剩幾天 = 剩下顆數 ÷ 每天吃幾顆
# - 每天吃幾顆 = 一次幾顆 × 一天幾個時段
# - 剩下顆數 = 總顆數 − 每天吃幾顆 × 從看診日到今天過了幾天（沒有記錄實際服藥，假設都有按時吃）
# - 沒有總顆數時，用藥單的給藥天數推算（天數 × 每天吃幾顆）
# - 藥單還剩幾天、吃完日：取藥單內最晚吃完的藥


def daily_amount(dose_qty: Decimal, slots: Iterable[str]) -> Decimal:
    """每天吃幾顆。"""
    return dose_qty * len(list(slots))


def supply_days(dose_qty: Decimal, slots: Iterable[str], quantity: Decimal | None, days: int | None) -> int:
    """這個藥總共可以吃幾天（總顆數 ÷ 每天吃幾顆，無條件捨去）；總顆數與天數都沒有時為 0。"""
    daily = daily_amount(dose_qty, slots)
    if quantity is None:
        return days or 0
    return int(quantity // daily) if daily > 0 else 0


def next_letter(used: set[str]) -> str | None:
    """吃藥中的藥單沒用到的第一個字母；A～Z 都用完時回傳 None。"""
    return next((letter for letter in LETTERS if letter not in used), None)


def code(letter: str, seq: int) -> str:
    """藥的編號，例如 A1。"""
    return f"{letter}{seq}"


def qty_label(qty: Decimal) -> str:
    """1 → 1 顆；0.5 → 半顆；1.5 → 1 顆半。"""
    whole, fraction = int(qty), qty - int(qty)
    if fraction == 0:
        return f"{whole} 顆"
    if fraction == Decimal("0.5"):
        return "半顆" if whole == 0 else f"{whole} 顆半"
    return f"{qty.normalize()} 顆"


def doses_text(items: list[tuple[str, Decimal]]) -> str:
    """推播用：「B1、B2 各 1 顆」；顆數不同時「A1 1 顆、A3 半顆」。"""
    if len({qty for _, qty in items}) == 1:
        codes = "、".join(c for c, _ in items)
        qty = qty_label(items[0][1])
        return f"{codes} 各 {qty}" if len(items) > 1 else f"{codes} {qty}"
    return "、".join(f"{c} {qty_label(q)}" for c, q in items)


# ---------- 同成分 ----------


def same_ingredient(
    new_license: str | None,
    new_ingredients: list[str],
    other_license: str | None,
    other_ingredients: list[str],
) -> bool:
    """同一個藥品代號，或主成分（ATC 7 碼）有重疊（不分大小寫）。"""
    if new_license and new_license == other_license:
        return True
    normalize_set = lambda items: {i.strip().lower() for i in items if i.strip()}  # noqa: E731
    return bool(normalize_set(new_ingredients) & normalize_set(other_ingredients))


# ---------- 藥名搜尋與辨識比對 ----------


def search_key(text: str) -> str:
    """比對用：全形轉半形、大寫、去掉空白以外的符號。"""
    return re.sub(r"[^\w\s/.%]", " ", normalize(text)).upper().strip()


def matches_prefix(query: str, *candidates: str | None) -> bool:
    """藥名搜尋：候選名稱（或其中任一個字）以查詢文字開頭，不分大小寫。"""
    q = search_key(query)
    for candidate in candidates:
        if not candidate:
            continue
        key = search_key(candidate)
        if key.startswith(q) or any(word.startswith(q) for word in key.split()):
            return True
    return False


def similarity(a: str, b: str) -> float:
    """兩個藥名的相似度（0～1），去掉空白後比較。"""
    a_key, b_key = search_key(a).replace(" ", ""), search_key(b).replace(" ", "")
    if not a_key or not b_key:
        return 0.0
    if a_key == b_key:
        return 1.0
    return difflib.SequenceMatcher(None, a_key, b_key).ratio()


def strength_number(strength: str | None) -> float:
    """劑量排序用：「2.5/1000 毫克」→ 2.5；拆不出數字時排最後。"""
    if strength and (match := re.match(r"\d+(?:\.\d+)?", strength)):
        return float(match.group())
    return float("inf")


def is_oral(form: str | None) -> bool:
    return bool(form) and any(hint in form for hint in ORAL_FORM_HINTS)  # type: ignore[operator]


# 英文產品名裡的劑型字，顯示藥名時去掉（劑型另外顯示）
_FORM_WORDS = re.compile(
    r"\b(FILM[- ]COATED|SUGAR[- ]COATED|ENTERIC[- ]COATED|ENTERIC[- ]MICROENCAPSULATED|MICROENCAPSULATED|"
    r"SUSTAINED[- ]RELEASE|EXTENDED[- ]RELEASE|PROLONGED[- ]RELEASE|CONTROLLED[- ]RELEASE|"
    r"F\.?C\.?|E\.?C\.?|S\.?R\.?|S\.?C\.?|TABLETS?|TABS?\.?|CAPSULES?|CAPS?\.?|CAPLETS?|GRANULES?|"
    r"ORAL|SOLUTION|SUSPENSION|SYRUP|INJECTION|INJ\.?)(?=\s|$)",
    re.IGNORECASE,
)


def display_name(product_en: str | None, fallback: str = "") -> str:
    """「NORVASC TABLETS」→「Norvasc」；「ANSIN E.C. TABLETS」→「Ansin」。去掉後沒有字時用原本的名稱。"""
    if not product_en:
        return fallback
    name = re.sub(r"\s+", " ", _FORM_WORDS.sub(" ", product_en)).strip(" ,.-")
    return (name or product_en).title()


# ---------- 藥袋 QR（前端格式，規格書 §8.1；和前端 utils/qr.ts 相同）----------

# 頻率代碼 → 時段（大小寫不拘）
FREQUENCY_CODE_SLOTS: dict[str, list[SlotKey]] = {
    "QD": [SlotKey.MORNING],
    "QAM": [SlotKey.MORNING],
    "QN": [SlotKey.BEDTIME],
    "HS": [SlotKey.BEDTIME],
    "QPM": [SlotKey.EVENING],
    "BID": [SlotKey.MORNING, SlotKey.EVENING],
    "Q12H": [SlotKey.MORNING, SlotKey.EVENING],
    "TID": [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING],
    "Q8H": [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING],
    "QID": [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING, SlotKey.BEDTIME],
    "Q6H": [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING, SlotKey.BEDTIME],
}
SLOT_BY_NAME: dict[str, SlotKey] = {label: key for key, label in SLOT_LABELS.items()} | {k.value: k for k in SlotKey}
MEAL_BY_NAME: dict[str, MealTiming] = {"飯前": MealTiming.BEFORE, "飯後": MealTiming.AFTER} | {m.value: m for m in MealTiming}
QR_DEFAULT_DAYS = 28  # 藥品沒有總顆數、藥單也沒有天數時


def qr_slots(slots: object, frequency: object) -> list[SlotKey]:
    """slots（早上／中午／晚上／睡前，或英文）優先；沒有時依頻率代碼；都沒有為早上。"""
    names = slots if isinstance(slots, list) else []
    keys = sort_slots(SLOT_BY_NAME[str(s)] for s in names if str(s) in SLOT_BY_NAME)
    if keys:
        return keys
    code = re.sub(r"\s", "", str(frequency or "")).upper()
    return FREQUENCY_CODE_SLOTS.get(code, [SlotKey.MORNING])


def qr_date(value: object, today: dt.date) -> dt.date:
    """YYYY-MM-DD、YYYY/MM/DD 或民國年 115.11.08；無法辨識時為今天。"""
    match = re.match(r"^(\d{2,4})[-/.](\d{1,2})[-/.](\d{1,2})$", str(value or "").strip())
    if not match:
        return today
    year, month, day = (int(g) for g in match.groups())
    try:
        return dt.date(year + 1911 if year < 1911 else year, month, day)
    except ValueError:
        return today
