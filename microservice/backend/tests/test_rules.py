import datetime as dt

from app.integrations.fda.importer import from_nhi
from app.modules.emergency_card import rules as card_rules
from app.modules.medication import rules as med_rules
from app.modules.medication.models import Frequency, MealTiming, SlotKey
from app.modules.speech import rules as speech


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
        assert speech.speak_time(t) == text


def test_qty_text() -> None:
    from decimal import Decimal

    assert speech.qty_text(Decimal("1.0")) == "1 顆"
    assert speech.qty_text(Decimal("0.5")) == "半顆"
    assert speech.qty_text(Decimal("1.5")) == "1 顆半"


def test_drug_name_prefers_chinese() -> None:
    # 同時有中英文：只念中文
    assert speech.drug_name("Norvasc 5mg", "脈優錠5毫克") == "脈優錠5毫克"
    assert speech.drug_name("脈優錠 5mg") == "脈優錠 5mg"
    # 只有英文：照原文念
    assert speech.drug_name("Amlodipine 5mg") == "Amlodipine 5mg"
    assert speech.drug_name("Amlodipine 5mg", None) == "Amlodipine 5mg"
    assert speech.drug_name("Amlodipine 5mg", "") == "Amlodipine 5mg"


def test_medication_card_speech() -> None:
    from decimal import Decimal

    text = speech.medication_card(
        number=3,
        drug="脈優錠",
        department="ENT 耳鼻喉科",
        purpose="Allergy 過敏",
        dose_qty=Decimal("2"),
        meal_label="飯前",
        times=[dt.time(17, 30), dt.time(7, 30)],
        days_left=0,
    )
    # 科別、用途仍不唸英文字母
    assert text == "3 號藥，脈優錠，耳鼻喉科開的，過敏。一次 2 顆，飯前吃，早上 7 點半、下午 5 點半。已經吃完了。"


def test_reminder_speech() -> None:
    from decimal import Decimal

    text = speech.reminder(
        title="Grandma 陳阿嬤",
        meal_word="飯後",
        items=[(1, "脈優錠", Decimal("2")), (3, "Metformin 500mg", Decimal("0.5"))],
    )
    assert text == "陳阿嬤，吃藥時間到囉～飯後吃：1 號 脈優錠 2 顆、3 號 Metformin 500mg 半顆"


def test_speech_unsupported_lang() -> None:
    import pytest

    with pytest.raises(ValueError):
        speech.speak_time(dt.time(8, 0), speech.Lang("nan"))  # 台語還沒做


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


# ---------- 英文朗讀稿 ----------


def test_english_drug_name() -> None:
    # 藥袋上的英文名優先，其次是許可證英文品名；只有中文就不念
    assert speech.drug_name_en("Amlodipine 5mg", "Norvasc") == "Amlodipine 5mg"
    assert speech.drug_name_en("脈優錠", "Norvasc 5mg") == "Norvasc 5mg"
    assert speech.drug_name_en("脈優錠 Norvasc 5mg") == "Norvasc 5mg"
    assert speech.drug_name_en("脈優錠") == ""


def test_english_glossary() -> None:
    assert speech.department_en("家醫科") == "Family Medicine"
    assert speech.department_en("ENT 耳鼻喉科") == "Ear, Nose and Throat"
    assert speech.department_en("不存在科") == ""
    assert speech.purpose_en("降血壓") == "blood pressure"
    assert speech.purpose_en("不明用途") == ""
    assert speech.title_en("陳阿嬤") == "Grandma Chen"
    assert speech.title_en("王先生") == "Mr. Wang"
    assert speech.title_en("阿公") == "Grandpa"
    assert speech.title_en("林媽媽") == "Mom"
    assert speech.title_en("路人") == ""


def test_english_time_and_qty() -> None:
    from decimal import Decimal

    en = speech.Lang.EN
    assert speech.speak_time(dt.time(8, 0), en) == "8 AM"
    assert speech.speak_time(dt.time(12, 0), en) == "12 PM"
    assert speech.speak_time(dt.time(13, 30), en) == "1:30 PM"
    assert speech.speak_time(dt.time(0, 0), en) == "12 AM"
    assert speech.qty_text(Decimal("1"), en) == "1 tablet"
    assert speech.qty_text(Decimal("2"), en) == "2 tablets"
    assert speech.qty_text(Decimal("0.5"), en) == "half a tablet"
    assert speech.qty_text(Decimal("1.5"), en) == "1 and a half tablets"


def test_english_medication_card() -> None:
    from decimal import Decimal

    text = speech.medication_card(
        number=1,
        drug="Amlodipine 5mg",
        department="家醫科",
        purpose="降血壓",
        dose_qty=Decimal("1"),
        meal_label="飯後",
        times=[dt.time(18, 0), dt.time(8, 0)],
        days_left=19,
        lang=speech.Lang.EN,
    )
    assert text == (
        "Medicine number 1, Amlodipine 5mg, from Family Medicine, for blood pressure. "
        "Take 1 tablet after meals, at 8 AM and 6 PM. 19 days left."
    )


def test_english_reminder() -> None:
    from decimal import Decimal

    text = speech.reminder(
        title="陳阿嬤",
        meal_word="飯後",
        items=[(1, "Amlodipine 5mg", Decimal("2")), (3, "", Decimal("0.5"))],
        lang=speech.Lang.EN,
    )
    assert text == (
        "Grandma Chen, it's time for your medicine. After meals: number 1, Amlodipine 5mg, 2 tablets; number 3, half a tablet."
    )
