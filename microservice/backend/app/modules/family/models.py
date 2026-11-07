import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPrimaryKey


class FamilyInvite(UUIDPrimaryKey, CreatedAt, Base):
    """6 位數邀請碼，10 分鐘後失效，只能用一次。"""

    __tablename__ = "family_invites"

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class FamilyBinding(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "family_bindings"
    __table_args__ = (
        Index(
            "uq_family_bindings_active_pair",
            "elder_id",
            "family_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    elder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    # 家人對長輩的稱呼，例如「媽媽」，用於推播文字
    relation_label: Mapped[str] = mapped_column(String(20))
    notify_on_ack: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # NULL 表示還能做一次初始設定（規格書 §3.2）
    setup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
