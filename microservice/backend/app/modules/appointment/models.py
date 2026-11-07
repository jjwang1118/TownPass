import datetime as dt
import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, SmallInteger, String, Time, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey, enum_column


class Period(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class SessionStatus(StrEnum):
    OPEN = "open"
    SUSPENDED = "suspended"  # 停診


class AppointmentStatus(StrEnum):
    BOOKED = "booked"
    CANCELLED = "cancelled"


class Hospital(UUIDPrimaryKey, Base):
    """聯醫院區（模擬資料，正式版由 integrations/tpech 取得）。"""

    __tablename__ = "hospitals"

    name: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))


class Department(UUIDPrimaryKey, Base):
    __tablename__ = "departments"

    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id"), index=True)
    name: Mapped[str] = mapped_column(String(32))


class Doctor(UUIDPrimaryKey, Base):
    __tablename__ = "doctors"

    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"), index=True)
    name: Mapped[str] = mapped_column(String(32))


class ClinicSession(UUIDPrimaryKey, Base):
    """門診（某位醫師某天的上午、下午或晚上）。停診或每個時間都額滿時，前端顯示灰色不可選。"""

    __tablename__ = "clinic_sessions"
    __table_args__ = (UniqueConstraint("doctor_id", "date", "period"),)

    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id"), index=True)
    date: Mapped[dt.date]
    period: Mapped[Period] = mapped_column(enum_column(Period))
    issued_count: Mapped[int] = mapped_column(SmallInteger, default=0)  # 已發出的看診號碼，只增不減
    status: Mapped[SessionStatus] = mapped_column(enum_column(SessionStatus), default=SessionStatus.OPEN)


class ClinicSlot(UUIDPrimaryKey, Base):
    """門診裡的看診時間（例如上午 09:30），各自有名額（UI E10g）。"""

    __tablename__ = "clinic_slots"
    __table_args__ = (UniqueConstraint("session_id", "time"),)

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinic_sessions.id", ondelete="CASCADE"), index=True)
    time: Mapped[dt.time] = mapped_column(Time)
    capacity: Mapped[int] = mapped_column(SmallInteger)
    booked_count: Mapped[int] = mapped_column(SmallInteger, default=0)  # 目前有效預約數，取消會減少


class Appointment(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # 同一位長輩不能重複預約同一個門診
        Index(
            "uq_appointments_booked_session",
            "elder_id",
            "session_id",
            unique=True,
            postgresql_where=text("status = 'booked'"),
        ),
    )

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinic_sessions.id"), index=True)
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinic_slots.id"), index=True)
    visit_no: Mapped[int] = mapped_column(SmallInteger)  # 看診號碼
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_column(AppointmentStatus), default=AppointmentStatus.BOOKED
    )
    cancelled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # 回診前一天 18:00 自動推播長輩與家屬（UI E12、E16、F08）
    reminded_day_before_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
