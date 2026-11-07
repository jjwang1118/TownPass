import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamps, UUIDPrimaryKey, enum_column
from app.integrations.townpass.messages import PushPlatform


class DeviceToken(UUIDPrimaryKey, Timestamps, Base):
    """FCM token。一個使用者可以有多台裝置。"""

    __tablename__ = "device_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True)
    platform: Mapped[PushPlatform] = mapped_column(enum_column(PushPlatform))
