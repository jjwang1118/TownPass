import datetime as dt
import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, enum_column


class Frequency(StrEnum):
    """藥袋 QR、拍照辨識可能給的頻率，轉成時段後就不再使用。"""

    QD = "QD"  # 一天一次
    BID = "BID"  # 一天兩次
    TID = "TID"  # 一天三次
    QID = "QID"  # 一天四次
    HS = "HS"  # 睡前


class MealTiming(StrEnum):
    BEFORE = "before"
    AFTER = "after"


class SlotKey(StrEnum):
    """固定四個吃藥時段，時間見 rules.SLOT_TIMES。"""

    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"
    BEDTIME = "bedtime"


class PrescriptionSource(StrEnum):
    PHOTO = "photo"  # 拍藥袋照片（手機辨識）
    QR = "qr"  # 掃藥袋 QR Code
    MANUAL = "manual"  # 手動輸入


class PrescriptionStatus(StrEnum):
    ACTIVE = "active"  # 吃藥中
    FINISHED = "finished"  # 已吃完（字母釋放給新藥單）


class MedicationStatus(StrEnum):
    ACTIVE = "active"
    STOPPED = "stopped"


class StopReason(StrEnum):
    FINISHED = "finished"  # 吃完了
    DOCTOR_ADVISED = "doctor_advised"  # 醫生說不用吃了


class Prescription(UUIDPrimaryKey, Timestamps, Base):
    """藥單：一個藥袋一張，用字母（A、B…）標示，長輩在實體藥袋上寫上同一個字母。"""

    __tablename__ = "prescriptions"
    __table_args__ = (
        # 吃藥中的藥單，字母不可重複；吃完後字母釋放
        Index(
            "uq_prescriptions_active_letter",
            "elder_id",
            "letter",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    letter: Mapped[str] = mapped_column(String(1))
    source: Mapped[PrescriptionSource] = mapped_column(enum_column(PrescriptionSource))
    hospital: Mapped[str | None] = mapped_column(String(64))  # 手動新增時可之後補填
    department: Mapped[str | None] = mapped_column(String(64))
    doctor: Mapped[str | None] = mapped_column(String(64))
    visit_date: Mapped[dt.date]  # 看診日，從這天開始吃
    days: Mapped[int | None]  # 給藥天數；藥品沒有總顆數時用來推算
    status: Mapped[PrescriptionStatus] = mapped_column(
        enum_column(PrescriptionStatus), default=PrescriptionStatus.ACTIVE
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))  # 核對並加入的人


class Medication(UUIDPrimaryKey, Timestamps, Base):
    """藥單裡的一個藥，編號為「字母＋序號」，例如 A1。"""

    __tablename__ = "medications"
    __table_args__ = (UniqueConstraint("prescription_id", "seq"),)

    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True)
    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    seq: Mapped[int]
    name: Mapped[str] = mapped_column(String(128))
    license_no: Mapped[str | None] = mapped_column(String(64))  # 健保藥品代號
    strength: Mapped[str | None] = mapped_column(String(32))  # 劑量，例如「5 毫克」
    purpose: Mapped[str | None] = mapped_column(String(128))
    dose_qty: Mapped[Decimal] = mapped_column(Numeric(3, 1))  # 一次幾顆
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))  # 總顆數（藥袋上的數量）；還剩幾天 = 剩下顆數 ÷ 每天吃幾顆
    slots: Mapped[list[str]] = mapped_column(ARRAY(String(16)))  # SlotKey，依時間排序
    meal_timing: Mapped[MealTiming] = mapped_column(enum_column(MealTiming))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))  # 待核對
    status: Mapped[MedicationStatus] = mapped_column(
        enum_column(MedicationStatus), default=MedicationStatus.ACTIVE
    )
    stopped_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    stop_reason: Mapped[StopReason | None] = mapped_column(enum_column(StopReason))


class DrugLicense(Base):
    """藥品資料（健保用藥品項，只讀），用於同成分檢查與藥名搜尋。"""

    __tablename__ = "drug_licenses"

    license_no: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(256))
    name_en: Mapped[str | None] = mapped_column(String(256))
    ingredients: Mapped[list[str]] = mapped_column(ARRAY(Text))
    product_en: Mapped[str | None] = mapped_column(String(256), index=True)
    product_zh: Mapped[str | None] = mapped_column(String(256))
    ingredient_en: Mapped[str | None] = mapped_column(String(256))
    strength: Mapped[str | None] = mapped_column(String(32))
    form: Mapped[str | None] = mapped_column(String(32))
