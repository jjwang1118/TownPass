import datetime as dt

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
