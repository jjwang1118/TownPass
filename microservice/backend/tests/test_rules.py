import datetime as dt

from app.integrations.fda.importer import from_nhi
from app.modules.emergency_card import rules as card_rules
from app.modules.medication import rules as med_rules
from app.modules.medication.models import Frequency, MealTiming, SlotKey


def test_allocate_slots() -> None:
    assert med_rules.allocate_slots(Frequency.TID, MealTiming.AFTER) == [
        SlotKey.BREAKFAST_AFTER,
        SlotKey.LUNCH_AFTER,
        SlotKey.DINNER_AFTER,
    ]
    assert med_rules.allocate_slots(Frequency.QID, MealTiming.BEFORE)[-1] is SlotKey.BEDTIME
    assert med_rules.allocate_slots(Frequency.HS, MealTiming.AFTER) == [SlotKey.BEDTIME]
    assert med_rules.allocate_slots(Frequency.BID, MealTiming.BEDTIME) == [SlotKey.BEDTIME]


def test_days() -> None:
    start = dt.date(2026, 11, 1)
    assert med_rules.run_out_date(start, 28) == dt.date(2026, 11, 28)
    assert med_rules.days_left(start, 28, dt.date(2026, 11, 28)) == 1
    assert med_rules.days_left(start, 28, dt.date(2026, 12, 31)) == 0


def test_next_number_reuses_smallest() -> None:
    assert med_rules.next_number(set()) == 1
    assert med_rules.next_number({1, 3}) == 2


def test_card_code_roundtrip() -> None:
    code = card_rules.generate_code()
    assert card_rules.normalize_code(code) == code
    assert card_rules.normalize_code(code.lower().replace("-", " ")) == code
    assert card_rules.normalize_code("TPE-0000-0000") is None  # 0 不在字元表
    url = card_rules.qr_url("https://example.web.app/", code)
    assert card_rules.code_from_qr(url) == code
    assert card_rules.code_from_qr("https://example.web.app/other") is None


def test_days_left_before_start() -> None:
    assert med_rules.days_left(dt.date(2026, 11, 10), 28, dt.date(2026, 11, 1)) == 28


def test_speak_time() -> None:
    cases = {
        dt.time(7, 30): "早上 7 點半",
        dt.time(8, 0): "早上 8 點",
        dt.time(11, 30): "上午 11 點半",
        dt.time(12, 0): "中午 12 點",
        dt.time(13, 0): "下午 1 點",
        dt.time(17, 30): "下午 5 點半",
        dt.time(18, 0): "晚上 6 點",
        dt.time(21, 15): "晚上 9 點 15 分",
    }
    for t, text in cases.items():
        assert med_rules.speak_time(t) == text


def test_qty_text() -> None:
    from decimal import Decimal

    assert med_rules.qty_text(Decimal("1.0")) == "1 顆"
    assert med_rules.qty_text(Decimal("0.5")) == "半顆"
    assert med_rules.qty_text(Decimal("1.5")) == "1 顆半"


def test_speech_text_has_no_latin_letters() -> None:
    from decimal import Decimal

    text = med_rules.speech_text(
        number=3,
        department="ENT 耳鼻喉科",
        purpose="Allergy 過敏",
        dose_qty=Decimal("2"),
        meal_timing=MealTiming.BEFORE,
        times=[dt.time(17, 30), dt.time(7, 30)],
        days_left=0,
    )
    assert text == "3 號藥，耳鼻喉科開的，過敏。一次 2 顆，飯前吃，早上 7 點半、下午 5 點半。已經吃完了。"


def test_same_ingredient() -> None:
    assert med_rules.same_ingredient("A", [], "A", [])
    assert med_rules.same_ingredient("A", ["Amlodipine "], "B", ["amlodipine"])
    assert not med_rules.same_ingredient("A", ["metformin"], "B", ["amlodipine"])
    assert not med_rules.same_ingredient(None, [], None, [])


def test_from_nhi_uses_full_atc_only() -> None:
    item = {"藥品代號": "B021571100", "中文品名": "脈優錠５毫克", "英文品名": "NORVASC TABLETS 5MG", "ATC代碼": "C08CA01"}
    assert from_nhi(item) == {
        "license_no": "B021571100",
        "name_zh": "脈優錠５毫克",
        "name_en": "NORVASC TABLETS 5MG",
        "ingredients": ["C08CA01"],
    }
    # 3～5 碼只是藥物類別（R05X 感冒複方），不拿來比對同成分
    assert from_nhi({**item, "ATC代碼": "R05X"})["ingredients"] == []
