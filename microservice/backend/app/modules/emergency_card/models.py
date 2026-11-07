import datetime as dt
import uuid
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey, enum_column
from app.core.security import EncryptedJSON, EncryptedText


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodType(StrEnum):
    A = "A"
    B = "B"
    O = "O"
    AB = "AB"
    UNKNOWN = "unknown"  # 不知道


class AccessMethod(StrEnum):
    QR = "qr"
    MANUAL = "manual"


class ConsentType(StrEnum):
    HEALTH_DATA = "health_data"


class EmergencyCard(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "emergency_cards"

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(EncryptedText)  # 姓名；吃藥提醒推播給家屬時也用
    birth_date: Mapped[dt.date | None]  # API 必填；舊資料（只有出生年）為 null
    gender: Mapped[Gender | None] = mapped_column(enum_column(Gender))
    blood_type: Mapped[BloodType] = mapped_column(enum_column(BloodType), default=BloodType.UNKNOWN)
    # 個資法第 6 條特種個資：加密儲存
    chronic_conditions: Mapped[list[str] | None] = mapped_column(EncryptedJSON)
    allergies: Mapped[list[dict[str, Any]] | None] = mapped_column(EncryptedJSON)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class EmergencyContact(UUIDPrimaryKey, Base):
    """每張卡 1 位（UI E14：只能填一位，不提供新增第二位）。"""

    __tablename__ = "emergency_contacts"

    card_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("emergency_cards.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(EncryptedText)
    relation: Mapped[str] = mapped_column(String(20))
    phone: Mapped[str] = mapped_column(EncryptedText)
    sort_order: Mapped[int] = mapped_column(SmallInteger)


class CardCode(CreatedAt, Base):
    """卡號紀錄。重新產生後舊卡號 revoked_at 有值，立即失效。"""

    __tablename__ = "card_codes"
    __table_args__ = (
        Index(
            "uq_card_codes_active_card",
            "card_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    card_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("emergency_cards.id", ondelete="CASCADE"))
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class CardAccessLog(UUIDPrimaryKey, Base):
    """救護人員查看紀錄。只新增，不提供修改或刪除。"""

    __tablename__ = "card_access_logs"

    card_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("emergency_cards.id"), index=True)
    responder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("responders.id"))
    # 查看當下的姓名與分隊（之後離職或調動，紀錄也不變）
    responder_name: Mapped[str] = mapped_column(String(32))
    responder_unit: Mapped[str] = mapped_column(String(32))
    responder_staff_no: Mapped[str | None] = mapped_column(String(32))  # 人員編號
    code_used: Mapped[str] = mapped_column(String(16))
    method: Mapped[AccessMethod] = mapped_column(enum_column(AccessMethod))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    accessed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class Consent(UUIDPrimaryKey, Base):
    __tablename__ = "consents"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[ConsentType] = mapped_column(enum_column(ConsentType))
    granted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
