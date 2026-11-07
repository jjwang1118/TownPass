import datetime as dt
from decimal import Decimal

from app.integrations.fda.importer import from_nhi, parse_name
from app.modules.appointment import rules as appt_rules
from app.modules.appointment.models import Period
from app.modules.emergency_card import rules as card_rules
from app.modules.medication import rules as med_rules
from app.modules.medication.models import Frequency, SlotKey
from app.modules.speech import rules as speech


def test_fixed_slots() -> None:
    # 固定四個時段：09:00、12:00、18:00、22:00
    assert [(med_rules.SLOT_LABELS[s], med_rules.SLOT_TIMES[s].hour) for s in med_rules.SLOT_ORDER] == [
        ("早上", 9),
        ("中午", 12),
        ("晚上", 18),
        ("睡前", 22),
    ]
    assert med_rules.FREQUENCY_SLOTS[Frequency.TID] == [SlotKey.MORNING, SlotKey.NOON, SlotKey.EVENING]
    assert med_rules.FREQUENCY_SLOTS[Frequency.HS] == [SlotKey.BEDTIME]
    assert med_rules.sort_slots(["bedtime", "morning", "morning"]) == [SlotKey.MORNING, SlotKey.BEDTIME]


def test_days() -> None:
    start = dt.date(2026, 11, 1)
    assert med_rules.run_out_date(start, 28) == dt.date(2026, 11, 28)
    assert med_rules.days_left(start, 28, dt.date(2026, 11, 28)) == 1
    assert med_rules.days_left(start, 28, dt.date(2026, 12, 31)) == 0


def test_next_letter_reuses_smallest() -> None:
    assert med_rules.next_letter(set()) == "A"
    assert med_rules.next_letter({"A", "C"}) == "B"
    assert med_rules.next_letter(set(med_rules.LETTERS)) is None
    assert med_rules.code("A", 2) == "A2"


def test_doses_text() -> None:
    # 推播：「B1、B2 各 1 顆」；顆數不同時分開寫
    assert med_rules.doses_text([("B1", Decimal(1)), ("B2", Decimal(1))]) == "B1、B2 各 1 顆"
    assert med_rules.doses_text([("A3", Decimal("0.5"))]) == "A3 半顆"
    assert med_rules.doses_text([("A1", Decimal(1)), ("C1", Decimal("0.5"))]) == "A1 1 顆、C1 半顆"


def test_search_helpers() -> None:
    assert med_rules.matches_prefix("asp", "ASPIRIN E.C. TABLETS")
    assert med_rules.matches_prefix("阿斯", "阿斯匹靈腸衣錠")
    assert med_rules.matches_prefix("tab", "NORVASC TABLETS")  # 其中一個字開頭也算
    assert not med_rules.matches_prefix("vasc", "NORVASC TABLETS")
    assert med_rules.display_name("NORVASC TABLETS") == "Norvasc"
    assert med_rules.display_name("TRAJENTA DUO FILM-COATED TABLETS") == "Trajenta Duo"
    assert med_rules.similarity("Norvsac", "NORVASC") > med_rules.NAME_MATCH_MIN
    assert med_rules.similarity("abc", "NORVASC") < med_rules.NAME_MATCH_MIN
    assert med_rules.strength_number("2.5/1000 毫克") == 2.5


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
    item = {
        "藥品代號": "B021571100",
        "中文品名": "脈優錠５毫克",
        "英文品名": "NORVASC TABLETS 5MG",
        "ATC代碼": "C08CA01",
        "劑型": "錠劑",
    }
    assert from_nhi(item) == {
        "license_no": "B021571100",
        "name_zh": "脈優錠５毫克",
        "name_en": "NORVASC TABLETS 5MG",
        "ingredients": ["C08CA01"],
        "product_en": "NORVASC TABLETS",
        "product_zh": "脈優錠",
        "ingredient_en": None,
        "strength": "5 毫克",
        "form": "錠劑",
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


def test_parse_name() -> None:
    # 去掉劑量、藥廠（引號）、括號，拆出主成分與劑量；全形數字轉半形
    assert parse_name('Amcopine Tablets 10mg "H.S." (Amlodipine)', '"華興"壓可平錠10毫克 (安脈狄平)') == (
        "AMCOPINE TABLETS",
        "壓可平錠",
        "AMLODIPINE",
        "10 毫克",
    )
    assert parse_name("Trajenta Duo 2.5/1000mg Film-Coated Tablets", "糖倍平 膜衣錠 2.5/1000 毫克")[3] == "2.5/1000 毫克"
    assert parse_name("SOME CREAM", "某某乳膏")[3] is None


def test_slot_speech() -> None:
    # UI E02：依科別分組念序號與顆數，不念英文字母與藥名
    groups = [("B", "新陳代謝科", [(1, Decimal(1)), (2, Decimal(1))])]
    assert speech.slot(time=dt.time(12, 0), groups=groups) == "中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆"
    assert speech.slot(time=dt.time(22, 0), groups=[("A", "", [(3, Decimal("0.5"))])]) == "晚上 10 點，要吃另一包藥 3 號 半顆"
    assert speech.slot(time=dt.time(12, 0), groups=groups, lang=speech.Lang.EN) == (
        "12 PM medicine: Endocrinology and Metabolism, number 1, 1 tablet; number 2, 1 tablet."
    )


def test_age() -> None:
    assert card_rules.age(dt.date(1948, 5, 12), dt.date(2026, 11, 7)) == 78
    assert card_rules.age(dt.date(1948, 11, 8), dt.date(2026, 11, 7)) == 77
    assert card_rules.age(None, dt.date(2026, 11, 7)) is None


def test_appointment_labels() -> None:
    assert appt_rules.date_label(dt.date(2026, 11, 14)) == "11/14（六）"
    assert appt_rules.time_label(Period.MORNING, dt.time(9, 30)) == "上午 09:30"
    assert appt_rules.remaining_label(3) == "還有 3 個名額"
    assert appt_rules.remaining_label(0) == "已額滿"
    sessions = [
        (dt.date(2026, 11, 9), Period.MORNING),  # 一
        (dt.date(2026, 11, 13), Period.MORNING),  # 五
        (dt.date(2026, 11, 16), Period.MORNING),  # 一（重複的星期只列一次）
        (dt.date(2026, 11, 10), Period.EVENING),  # 二
    ]
    assert appt_rules.weekly_schedule(sessions) == "週一、週五 上午；週二 晚上"
    title, body = appt_rules.elder_reminder(
        at=dt.time(9, 30), hospital="臺北市立聯合醫院仁愛院區", department="心臟內科", doctor="林醫師"
    )
    assert (title, body) == ("明天 09:30 要回診", "仁愛院區心臟內科林醫師，記得帶健保卡")
