from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, enum_column
from app.core.security import EncryptedText


class UserRole(StrEnum):
    ELDER = "elder"
    FAMILY = "family"


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    townpass_id: Mapped[str] = mapped_column(String(64), unique=True)
    # 第一次使用時才選擇，選擇前為 NULL
    role: Mapped[UserRole | None] = mapped_column(enum_column(UserRole))
    real_name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(EncryptedText)
    birth_year: Mapped[int | None]
