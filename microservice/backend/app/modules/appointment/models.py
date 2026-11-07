import datetime as dt
import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
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
    """門診。額滿或停診時前端顯示灰色不可選。"""

    __tablename__ = "clinic_sessions"
    __table_args__ = (UniqueConstraint("doctor_id", "date", "period"),)

    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id"), index=True)
    date: Mapped[dt.date]
    period: Mapped[Period] = mapped_column(enum_column(Period))
    capacity: Mapped[int] = mapped_column(SmallInteger)
    booked_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    status: Mapped[SessionStatus] = mapped_column(enum_column(SessionStatus), default=SessionStatus.OPEN)


class Appointment(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "appointments"

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinic_sessions.id"))
    visit_no: Mapped[int] = mapped_column(SmallInteger)  # 看診號碼
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_column(AppointmentStatus), default=AppointmentStatus.BOOKED
    )
