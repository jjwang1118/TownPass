"""拍藥袋（OCR 文字）：把手機端 OCR 辨識出的每一行文字整理成拍照辨識的欄位 PhotoIn（規格書 §8.3）。

OCR 在手機上做（比賽規定推論在裝置端），後端只收文字，用固定規則與對照表整理，不呼叫任何 AI。
整理好的 PhotoIn 交給 MedicationService.preview_photo()，和「拍照辨識」走同一套比對健保藥品資料、
信心分數與「電腦不確定這一項」的流程。

本檔是純函式，沒有 I/O。原則：
- 認不出來的欄位留空，不猜（preview_photo 會填預設值並列入不確定）。
- 從有標籤的字取出（例如「科別：家醫科」）視為有把握；只靠對照表或寫法猜的（例如單獨的「半顆」）
  信心分數給 GUESS，低於門檻，畫面上會紅框請長輩核對。
"""

import datetime as dt
import re
import unicodedata
from decimal import Decimal

from app.modules.medication import rules
from app.modules.medication.models import Frequency, MealTiming, SlotKey
from app.modules.medication.schemas import PhotoIn, PhotoItemIn
from app.modules.speech.glossary import DEPARTMENTS, PURPOSES

GUESS = 0.6  # 只靠對照表或寫法猜的欄位（低於 rules.CONFIDENCE_THRESHOLD）
UNLABELED_DATE = 0.7  # 沒有「調劑日、就診日」等字樣的日期

_CJK = r"一-鿿"
_NUM = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4}
_FREQ_BY_COUNT = {1: Frequency.QD, 2: Frequency.BID, 3: Frequency.TID, 4: Frequency.QID}


def normalize(line: str) -> str:
    """全形轉半形（NFKC）、「台北」統一為「臺北」、連續空白合成一個。"""
    text = unicodedata.normalize("NFKC", line).replace("台北", "臺北")
    return re.sub(r"\s+", " ", text).strip()


# ---------- 藥單層級：院區、科別、醫師、看診日、天數 ----------

_TPECH = re.compile(rf"(?:臺北市立聯合醫院|北市聯醫|聯合醫院)\s*[(（]?\s*([{_CJK}]{{1,6}}院區)")
_HOSPITAL = re.compile(rf"([{_CJK}]{{2,20}}(?:醫院|診所)(?:\s*[{_CJK}]{{1,6}}院區)?)")


def parse_hospital(text: str) -> str | None:
    if m := _TPECH.search(text):
        return f"臺北市立聯合醫院{m.group(1)}"
    if m := _HOSPITAL.search(text):
        return re.sub(r"\s+", "", m.group(1))[:64]
    return None


_DEPT_LABEL = re.compile(rf"科別\s*[:：]?\s*([{_CJK}]{{1,8}}科)")
# 「急診」常出現在注意事項（不適請至急診），不當作科別
_KNOWN_DEPARTMENTS = [d for d in DEPARTMENTS if d != "急診"]


def _longest_known(text: str, words: list[str]) -> str | None:
    found = [w for w in words if w in text]
    return max(found, key=len) if found else None


def parse_department(text: str) -> tuple[str | None, bool]:
    """回傳（科別, 是否有標籤）。"""
    if m := _DEPT_LABEL.search(text):
        return m.group(1), True
    return _longest_known(text, _KNOWN_DEPARTMENTS), False


_DOCTOR_LABEL = re.compile(rf"醫[師生]\s*[:：]\s*([{_CJK}]{{1,4}})")
# 「林醫師」要單獨成詞，避免「請遵照醫師指示」這類句子
_DOCTOR_SUFFIX = re.compile(rf"(?:^|[\s:：])([{_CJK}]{{1,3}}醫師)(?=$|[\s,，])")


def parse_doctor(lines: list[str]) -> str | None:
    for pattern in (_DOCTOR_LABEL, _DOCTOR_SUFFIX):
        for line in lines:
            if m := pattern.search(line):
                return m.group(1)
    return None


_DATE = re.compile(r"(?<!\d)(\d{3,4})\s*[./\-年]\s*(\d{1,2})\s*[./\-月]\s*(\d{1,2})(?!\d)")
_DATE_LABEL = re.compile(r"調劑|領藥|開立|就診|看診|處方|給藥日|日期")
_EXPIRY = re.compile(r"有效|保存|期限|到期")


def _to_date(year: str, month: str, day: str) -> dt.date | None:
    y = int(year)
    if y < 1911:  # 民國年，例如 115 → 2026
        y += 1911
    if not 2000 <= y <= 2100:
        return None
    try:
        return dt.date(y, int(month), int(day))
    except ValueError:
        return None


def parse_visit_date(lines: list[str]) -> tuple[dt.date | None, bool]:
    """回傳（看診日, 是否有標籤）。優先取有「調劑日、就診日」等字樣的那一行；有效期限不算。"""
    labeled: list[dt.date] = []
    others: list[dt.date] = []
    for line in lines:
        if _EXPIRY.search(line):
            continue
        for m in _DATE.finditer(line):
            if date := _to_date(*m.groups()):
                (labeled if _DATE_LABEL.search(line) else others).append(date)
    if labeled:
        return labeled[0], True
    return (others[0], False) if others else (None, False)


_DAYS = (
    re.compile(r"(?:給藥|用藥|服藥)?(?:天數|日數)\s*[:：]?\s*(\d{1,3})"),
    re.compile(r"共\s*(\d{1,3})\s*(?:天|日)(?!\s*份?\s*[顆粒錠片包])"),
    # 「1天3次」的 1天 是頻率，不是天數
    re.compile(r"(?<!\d)(\d{1,3})\s*(?:天份|日份|天分|日分|天)(?!數)(?!\s*[1-4一二兩三四]\s*次)"),
)


def parse_days(text: str) -> int | None:
    for pattern in _DAYS:
        if m := pattern.search(text):
            days = int(m.group(1))
            if 0 < days <= 365:
                return days
    return None


# ---------- 藥品層級 ----------

_STRENGTH = re.compile(
    r"(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)\s*(毫克|公絲|MG|微克|MCG|公克|G)(?![A-Z])", re.IGNORECASE
)
_UNIT = {"毫克": "毫克", "公絲": "毫克", "MG": "毫克", "微克": "微克", "MCG": "微克", "公克": "公克", "G": "公克"}


def parse_strength(line: str) -> tuple[str | None, str]:
    """回傳（劑量, 去掉劑量後的文字）。劑量寫法和健保資料一致，例如「5 毫克」「2.5/1000 毫克」。"""
    m = _STRENGTH.search(line)
    if not m:
        return None, line
    number = re.sub(r"\s+", "", m.group(1))
    return f"{number} {_UNIT[m.group(2).upper()]}", (line[: m.start()] + " " + line[m.end() :]).strip()


_NAME_LABEL = re.compile(r"(?:藥名|品名|藥品名稱)\s*[:：]?\s*")
_DRUG_FORM = re.compile(r"錠|膠囊|糖漿|顆粒|乳膏|軟膏|貼片|口服液|TABLET|CAPSULE", re.IGNORECASE)
# 用法、說明等不是藥名的行
_NOT_NAME = re.compile(
    r"每次|一次|每日|每天|一天|用法|用途|適應症|作用|醫師|醫院|院區|科別|日期|天數|總量|副作用|注意|姓名|病歷"
)
# 單獨的劑型字（「Amlodipine 錠」「Metformin Tablets」），不是藥名的一部分
_FORM_TOKEN = re.compile(r"(?:^|\s)(?:錠|膠囊|TABLETS?|TABS?\.?|CAPSULES?|CAPS?\.?|F\.?C\.?)(?=\s|$)", re.IGNORECASE)


def is_drug_line(line: str) -> bool:
    """這一行是不是一個藥的開頭：有「藥名：」，或有劑型、劑量而且不是用法說明。"""
    if _NAME_LABEL.match(line):
        return True
    return bool(_DRUG_FORM.search(line) or _STRENGTH.search(line)) and not _NOT_NAME.search(line)


def parse_drug_name(line: str) -> tuple[str | None, str | None]:
    """藥名那一行 →（藥名, 劑量）。藥名去掉標籤、劑量與單獨的劑型字，交給 preview_photo 比對健保資料。"""
    text = _NAME_LABEL.sub("", line, count=1)
    strength, text = parse_strength(text)
    name = re.sub(r"\s+", " ", _FORM_TOKEN.sub(" ", text)).strip(" ,，、")
    return (name[:128] or None), strength


_FREQ_ZH = re.compile(r"(?:一天|每天|每日|一日|1日|1天)\s*([1-4一二兩三四])\s*次")
_FREQ_CODE = re.compile(r"(?<![A-Z0-9])(" + "|".join(sorted(rules.FREQUENCY_CODE_SLOTS, key=len, reverse=True)) + r")(?![A-Z0-9])")


def parse_slots(text: str) -> tuple[list[SlotKey] | None, Frequency | None]:
    """回傳（時段, 頻率），擇一。寫明時段（早上、三餐、睡前…）優先，其次頻率代碼與「一天 N 次」。"""
    named = [key for key, label in rules.SLOT_LABELS.items() if label in text]
    if "早晚" in text:
        named += [SlotKey.MORNING, SlotKey.EVENING]
    if "三餐" in text:
        named += [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING]
    if named:
        return rules.sort_slots(named), None
    if m := _FREQ_CODE.search(text.upper()):
        return list(rules.FREQUENCY_CODE_SLOTS[m.group(1)]), None
    if m := _FREQ_ZH.search(text):
        return None, _FREQ_BY_COUNT[_NUM.get(m.group(1)) or int(m.group(1))]
    return None, None


def parse_meal_timing(text: str) -> MealTiming | None:
    upper = text.upper()
    if re.search(r"飯前|餐前|空腹", text) or re.search(r"(?<![A-Z])AC(?![A-Z])", upper):
        return MealTiming.BEFORE
    if re.search(r"飯後|餐後", text) or re.search(r"(?<![A-Z])PC(?![A-Z])", upper):
        return MealTiming.AFTER
    return None  # 只寫「睡前」時是時段，不是飯前飯後


_UNITS = r"(?:顆|粒|錠|片|包|膠囊)"
_QTY = re.compile(rf"(?:每次|一次|每回)\s*(?:服用|吃|口服)?\s*(\d+(?:\.\d+)?|1/2|半|[一二兩三四])\s*{_UNITS}")
# 沒有「每次」時：單獨的「半顆」「睡前一顆」。前面不能是冒號，避免「總量：28顆」
_QTY_BARE = re.compile(rf"(?:^|[\s,，、前後上午])(\d(?:\.\d)?|1/2|半|[一二兩三四])\s*{_UNITS}", re.MULTILINE)


def _qty(raw: str) -> Decimal | None:
    if raw in ("半", "1/2"):
        qty = Decimal("0.5")
    elif raw in _NUM:
        qty = Decimal(_NUM[raw])
    else:
        qty = Decimal(raw)
    # 與 PhotoItemIn.dose_qty 相同限制：大於 0、最多 3 位數、1 位小數
    if qty <= 0 or qty >= 100 or qty != qty.quantize(Decimal("0.1")):
        return None
    return qty


def parse_dose_qty(text: str) -> tuple[Decimal | None, bool]:
    """回傳（一次幾顆, 是否有「每次」）。單獨出現的只接受 4 顆以下，多半是總量的不算。"""
    if m := _QTY.search(text):
        return _qty(m.group(1)), True
    if m := _QTY_BARE.search(text):
        qty = _qty(m.group(1))
        if qty is not None and qty <= 4:
            return qty, False
    return None, False


_QUANTITY = re.compile(rf"(?:總量|總數|數量|共)\s*[:：]?\s*(\d{{1,4}}(?:\.\d)?)\s*{_UNITS}")


def parse_quantity(text: str) -> Decimal | None:
    """總顆數，例如「總量：28顆」「共84粒」。"""
    if m := _QUANTITY.search(text):
        quantity = Decimal(m.group(1))
        return quantity if 0 < quantity < Decimal(1000000) else None
    return None


# 「副作用」「主治醫師」不是用途
_PURPOSE_LABEL = re.compile(r"(?:用途|適應症|(?<!副)作用|主治(?!醫師)|功效|藥效)\s*[:：]?\s*([^\s:：,，。;；]{1,30})")


def parse_purpose(text: str, exclude: list[str]) -> tuple[str | None, bool]:
    """回傳（用途, 是否有標籤）。沒有標籤時才查對照表，不看副作用那一行與科別名稱。"""
    if m := _PURPOSE_LABEL.search(text):
        return m.group(1), True
    text = re.sub(r"副作用[^\n]*", "", text)
    for word in exclude:  # 「心臟內科」裡的「心臟」不是用途
        text = text.replace(word, "")
    return _longest_known(text, list(PURPOSES)), False


def _parse_item(block: list[str], department: str | None) -> PhotoItemIn:
    text = "\n".join(block)
    name, strength = parse_drug_name(block[0]) if is_drug_line(block[0]) else (None, None)
    slots, frequency = parse_slots(text)
    dose_qty, dose_labeled = parse_dose_qty(text)
    purpose, purpose_labeled = parse_purpose(text, [department] if department else [])
    confidence: dict[str, float] = {}
    if dose_qty is not None and not dose_labeled:
        confidence["dose_qty"] = GUESS
    if purpose and not purpose_labeled:
        confidence["purpose"] = GUESS
    return PhotoItemIn(
        name=name,
        strength=strength,
        purpose=purpose,
        dose_qty=dose_qty,
        quantity=parse_quantity(text),
        slots=slots,
        frequency=frequency,
        meal_timing=parse_meal_timing(text),
        confidence=confidence,
    )


def split_items(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """分成（藥單抬頭, 每個藥一段）。每個藥從藥名那一行開始，到下一個藥名之前。找不到藥名時整段當一個藥。"""
    starts = [i for i, line in enumerate(lines) if is_drug_line(line)]
    if not starts:
        return lines, [lines]
    header = lines[: starts[0]]
    blocks = [lines[s:e] for s, e in zip(starts, [*starts[1:], len(lines)], strict=True)]
    return header, blocks


# ---------- 整合 ----------


def parse(raw_lines: list[str]) -> PhotoIn | None:
    """OCR 文字 → PhotoIn；一個欄位都認不出來時回傳 None。最多 20 個藥（PhotoIn 的上限）。"""
    lines = [n for n in (normalize(line) for line in raw_lines) if n]
    if not lines:
        return None
    text = "\n".join(lines)
    _, blocks = split_items(lines)
    department, dept_labeled = parse_department(text)
    visit_date, date_labeled = parse_visit_date(lines)
    confidence: dict[str, float] = {}
    if department and not dept_labeled:
        confidence["department"] = GUESS
    if visit_date and not date_labeled:
        confidence["visit_date"] = UNLABELED_DATE

    photo = PhotoIn(
        hospital=parse_hospital(text),
        department=department,
        doctor=parse_doctor(lines),
        visit_date=visit_date,
        days=parse_days(text),
        items=[_parse_item(block, department) for block in blocks[:20]],
        confidence=confidence,
    )
    header = photo.model_dump(include={"hospital", "department", "doctor", "visit_date", "days"})
    items = [i.model_dump(exclude={"confidence"}) for i in photo.items]
    if not any(header.values()) and not any(v for item in items for v in item.values()):
        return None
    return photo
