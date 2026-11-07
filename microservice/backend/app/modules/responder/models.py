from enum import StrEnum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDPrimaryKey, enum_column


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    RESIGNED = "resigned"


class Responder(UUIDPrimaryKey, Base):
    """模擬消防局人員名冊（EMT-001～003）。正式版改由 integrations/fire_dept 查詢。"""

    __tablename__ = "responders"

    account: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(32))
    unit: Mapped[str] = mapped_column(String(32))  # 所屬分隊
    unit_phone: Mapped[str] = mapped_column(String(20))  # 分隊電話，查看救命卡後讓家人一鍵撥號
    title: Mapped[str] = mapped_column(String(32))  # 職稱
    employment_status: Mapped[EmploymentStatus] = mapped_column(enum_column(EmploymentStatus))
    has_ems_permission: Mapped[bool] = mapped_column(Boolean)
