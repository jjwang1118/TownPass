import uuid
import datetime as dt
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Numeric, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, enum_column


class Frequency(StrEnum):
    QD = "QD"  # 一天一次
    BID = "BID"  # 一天兩次
    TID = "TID"  # 一天三次
    QID = "QID"  # 一天四次
    HS = "HS"  # 睡前


class MealTiming(StrEnum):
    BEFORE = "before"
    AFTER = "after"
    BEDTIME = "bedtime"


class MedicationSource(StrEnum):
    QR = "qr"
    TPECH = "tpech"  # 帶入聯醫用藥（下一期）
    MANUAL = "manual"  # 手動輸入（下一期）


class MedicationStatus(StrEnum):
    ACTIVE = "active"
    STOPPED = "stopped"


class StopReason(StrEnum):
    FINISHED = "finished"  # 吃完了
    DOCTOR_ADVISED = "doctor_advised"  # 醫生說不用吃了


class SlotKey(StrEnum):
    BREAKFAST_BEFORE = "breakfast_before"
    BREAKFAST_AFTER = "breakfast_after"
    LUNCH_BEFORE = "lunch_before"
    LUNCH_AFTER = "lunch_after"
    DINNER_BEFORE = "dinner_before"
    DINNER_AFTER = "dinner_after"
    BEDTIME = "bedtime"


class Medication(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "medications"
    __table_args__ = (
        # 進行中的藥，編號不可重複；停用後編號釋放
        Index(
            "uq_medications_active_number",
            "elder_id",
            "number",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    number: Mapped[int]
    name: Mapped[str] = mapped_column(String(128))
    license_no: Mapped[str | None] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(128))
    dose_qty: Mapped[Decimal] = mapped_column(Numeric(3, 1))
    frequency: Mapped[Frequency] = mapped_column(enum_column(Frequency))
    meal_timing: Mapped[MealTiming] = mapped_column(enum_column(MealTiming))
    start_date: Mapped[dt.date]
    days: Mapped[int]
    hospital: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(64))
    doctor: Mapped[str] = mapped_column(String(64))
    source: Mapped[MedicationSource] = mapped_column(enum_column(MedicationSource))
    status: Mapped[MedicationStatus] = mapped_column(
        enum_column(MedicationStatus), default=MedicationStatus.ACTIVE
    )
    stopped_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    stop_reason: Mapped[StopReason | None] = mapped_column(enum_column(StopReason))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class TimeSlot(Base):
    """每位長輩 7 個時段，預設值見 rules.DEFAULT_SLOT_TIMES。"""

    __tablename__ = "time_slots"

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    slot_key: Mapped[SlotKey] = mapped_column(enum_column(SlotKey), primary_key=True)
    time: Mapped[dt.time] = mapped_column(Time)


class DrugLicense(Base):
    """食藥署藥品許可證開放資料（只讀），用於同成分檢查。"""

    __tablename__ = "drug_licenses"

    license_no: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(256))
    name_en: Mapped[str | None] = mapped_column(String(256))
    ingredients: Mapped[list[str]] = mapped_column(ARRAY(Text))
