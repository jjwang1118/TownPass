"""拍藥袋（OCR 文字 → PhotoIn）的整理規則。純函式，不需要資料庫。"""

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.medication import ocr_text as ocr
from app.modules.medication import rules
from app.modules.medication.models import Frequency, MealTiming, SlotKey

SEED = Path(__file__).resolve().parents[1] / "seed" / "data"
RX = {s["file"]: s["payload"] for s in json.loads((SEED / "rx_samples.json").read_text(encoding="utf-8"))}
OCR_SAMPLES = json.loads((SEED / "ocr_samples.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("sample", "key"),
    [(s, key) for s in OCR_SAMPLES for key in ("lines", "tesseract_lines")],
    ids=[f"{s['rx']}-{key}" for s in OCR_SAMPLES for key in ("lines", "tesseract_lines")],
)
def test_samples_match_qr_payload(sample: dict, key: str) -> None:
    """同一張藥單，OCR 整理出的欄位要和藥袋 QR（前端格式）的內容一致；藥名比對健保資料在 API 測試。

    lines 是藥袋上的原文；tesseract_lines 是把原文畫成圖片後，前端同一套 tesseract.js（chi_tra＋eng、
    best_int、SINGLE_BLOCK）實際辨識的結果，含「：」變「 : 」、多出的符號、錯字（頭暈→頭量）等雜訊。
    """
    rx = RX[sample["rx"]]
    photo = ocr.parse(sample[key])
    assert photo is not None

    assert photo.hospital == "臺北市立聯合醫院" + rx["hospital"].split("（")[0]
    assert photo.department == rx["department"]
    assert photo.doctor == rx["doctor"]
    assert photo.visit_date == dt.date.fromisoformat(rx["visitDate"])
    assert photo.days == rx.get("days")
    assert len(photo.items) == len(rx["medicines"])
    for item, med in zip(photo.items, rx["medicines"], strict=True):
        # 藥袋印商品名（脈優錠、Lipitor），QR 範例寫學名，所以藥名在 API 測試比對健保碼；劑量要相同
        assert item.name
        assert item.strength == " ".join(med["name"].rsplit(" ", 2)[1:])
        assert item.purpose == med["effect"]
        assert item.dose_qty == Decimal(str(med["amount"]))
        assert item.quantity == Decimal(str(med["quantity"]))
        slots = item.slots or rules.FREQUENCY_SLOTS[item.frequency]  # type: ignore[index]
        assert slots == rules.qr_slots(med.get("slots"), med.get("frequency"))
        assert item.meal_timing == rules.MEAL_BY_NAME[med["meal"]]


def test_confidence_marks_guesses() -> None:
    """有標籤的欄位視為有把握；只靠對照表或寫法猜的給 GUESS，畫面上會紅框請長輩核對。"""
    labeled = ocr.parse(next(s["lines"] for s in OCR_SAMPLES if s["rx"] == "rx_a_cardiology"))
    assert labeled is not None
    assert labeled.confidence == {}
    assert all(item.confidence == {} for item in labeled.items)

    guessed = ocr.parse(next(s["lines"] for s in OCR_SAMPLES if s["rx"] == "rx_c_same_ingredient"))
    assert guessed is not None
    assert guessed.confidence == {"department": ocr.GUESS, "visit_date": ocr.UNLABELED_DATE}
    assert guessed.items[0].confidence == {"dose_qty": ocr.GUESS, "purpose": ocr.GUESS}


def test_unreadable_returns_none() -> None:
    assert ocr.parse(["", "  "]) is None
    assert ocr.parse(["Hello world", "12345"]) is None


def test_split_items() -> None:
    header, blocks = ocr.split_items(["仁愛院區", "脈優錠 5 毫克", "每次1顆", "藥名：阿斯匹靈", "飯後"])
    assert header == ["仁愛院區"]
    assert blocks == [["脈優錠 5 毫克", "每次1顆"], ["藥名：阿斯匹靈", "飯後"]]
    # 找不到藥名時整段當一個藥
    assert ocr.split_items(["每日一次", "飯後"]) == (["每日一次", "飯後"], [["每日一次", "飯後"]])


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Amlodipine 5 毫克錠", ("Amlodipine", "5 毫克")),
        ("藥名：Metformin 500 mg", ("Metformin", "500 毫克")),
        ("Aspirin 100mg Tablets", ("Aspirin", "100 毫克")),
        ("脈優錠 5 毫克", ("脈優錠", "5 毫克")),  # 中文品名裡的「錠」保留
        ("Janumet 50/1000 mg F.C. Tablets", ("Janumet", "50/1000 毫克")),
        ("Vitamin B12 500 mcg", ("Vitamin B12", "500 微克")),
        ("藥名：阿斯匹靈", ("阿斯匹靈", None)),
    ],
)
def test_drug_name_and_strength(line: str, expected: tuple[str | None, str | None]) -> None:
    assert ocr.parse_drug_name(ocr.normalize(line)) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("脈優錠 5 毫克", True),
        ("Aspirin 100mg Tablets", True),
        ("藥名：阿斯匹靈", True),
        ("每日1次 每次1顆", False),
        ("總量：28顆", False),
        ("用法：每日 500mg", False),
        ("臺北市立聯合醫院仁愛院區", False),
    ],
)
def test_is_drug_line(line: str, expected: bool) -> None:
    assert ocr.is_drug_line(line) is expected


@pytest.mark.parametrize(
    ("text", "slots", "frequency"),
    [
        ("早上 飯後", [SlotKey.MORNING], None),
        ("睡前", [SlotKey.BEDTIME], None),
        ("早晚各一次", [SlotKey.MORNING, SlotKey.EVENING], None),
        ("三餐飯後", [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING], None),
        ("三餐飯後及睡前", [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING, SlotKey.BEDTIME], None),
        ("TID PC", [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING], None),
        ("qn", [SlotKey.BEDTIME], None),
        ("Q12H", [SlotKey.MORNING, SlotKey.EVENING], None),
        ("每日1次", None, Frequency.QD),
        ("一天 三 次", None, Frequency.TID),
        ("1天2次", None, Frequency.BID),
        ("飯後", None, None),
        ("QIDX", None, None),  # 不是單獨的代碼
    ],
)
def test_slots(text: str, slots: list[SlotKey] | None, frequency: Frequency | None) -> None:
    assert ocr.parse_slots(ocr.normalize(text)) == (slots, frequency)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("飯前", MealTiming.BEFORE),
        ("空腹服用", MealTiming.BEFORE),
        ("QD AC", MealTiming.BEFORE),
        ("餐後", MealTiming.AFTER),
        ("TID PC", MealTiming.AFTER),
        ("睡前", None),  # 睡前是時段，不是飯前飯後
    ],
)
def test_meal_timing(text: str, expected: MealTiming | None) -> None:
    assert ocr.parse_meal_timing(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("每次1顆", (Decimal(1), True)),
        ("每次１.５粒", (Decimal("1.5"), True)),
        ("一次半顆", (Decimal("0.5"), True)),
        ("每次 1/2 錠", (Decimal("0.5"), True)),
        ("每次服用二顆", (Decimal(2), True)),
        ("早上 飯後 半顆", (Decimal("0.5"), False)),
        ("睡前一顆", (Decimal(1), False)),
        ("總量：28顆", (None, False)),  # 總量不是一次幾顆
        ("28顆", (None, False)),
        ("每次0.25顆", (None, True)),  # 超出 1 位小數
    ],
)
def test_dose_qty(text: str, expected: tuple[Decimal | None, bool]) -> None:
    assert ocr.parse_dose_qty(ocr.normalize(text)) == expected


def test_quantity_and_days() -> None:
    assert ocr.parse_quantity("總量：28顆") == Decimal(28)
    assert ocr.parse_quantity("共84粒") == Decimal(84)
    assert ocr.parse_quantity("每次1顆") is None
    assert ocr.parse_days("給藥天數：28") == 28
    assert ocr.parse_days("共14日") == 14
    assert ocr.parse_days("30日份") == 30
    assert ocr.parse_days("共84粒") is None  # 總顆數不是天數
    assert ocr.parse_days("1天3次") is None  # 頻率不是天數
    assert ocr.parse_days("給藥天數：0") is None


def test_visit_date() -> None:
    assert ocr.parse_visit_date(["115.11.01"]) == (dt.date(2026, 11, 1), False)
    assert ocr.parse_visit_date(["2026年11月3日"]) == (dt.date(2026, 11, 3), False)
    # 有效期限不算；有「調劑」字樣的優先
    assert ocr.parse_visit_date(["有效期限 116/10/31", "115/10/20", "調劑日 115/11/01"]) == (dt.date(2026, 11, 1), True)
    assert ocr.parse_visit_date(["115/13/40"]) == (None, False)
    assert ocr.parse_visit_date(["電話 02-2709-3600"]) == (None, False)


def test_header_fields() -> None:
    assert ocr.parse_hospital("北市聯醫 和平院區") == "臺北市立聯合醫院和平院區"
    assert ocr.parse_hospital("臺北市立聯合醫院（陽明院區）") == "臺北市立聯合醫院陽明院區"
    assert ocr.parse_hospital("仁心診所") == "仁心診所"
    assert ocr.parse_hospital("請按時服藥") is None
    assert ocr.parse_doctor(["主治醫師：李小明"]) == "李小明"
    assert ocr.parse_doctor(["家醫科 林醫師"]) == "林醫師"
    assert ocr.parse_doctor(["請遵照醫師指示服用"]) is None
    assert ocr.parse_department("科別：胸腔內科") == ("胸腔內科", True)
    assert ocr.parse_department("心臟血管內科門診") == ("心臟血管內科", False)  # 取最長的已知科別
    assert ocr.parse_department("不適請至急診") == (None, False)


def test_purpose() -> None:
    assert ocr.parse_purpose("用途：止痛", []) == ("止痛", True)
    assert ocr.parse_purpose("副作用：頭暈", []) == (None, False)
    assert ocr.parse_purpose("主治醫師：李小明", []) == (None, False)
    assert ocr.parse_purpose("心臟內科", ["心臟內科"]) == (None, False)
    assert ocr.parse_purpose("降血壓", []) == ("降血壓", False)
