"""user id_no hash

救護人員改以長者身分證字號查詢救命卡：使用者新增身分證字號的 HMAC（不存明碼）。

Revision ID: b7c3e1d2a4f5
Revises: a9dcbfe982d4
Create Date: 2026-11-08 07:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'b7c3e1d2a4f5'
down_revision: str | None = 'a9dcbfe982d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('id_no_hash', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_users_id_no_hash'), 'users', ['id_no_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_id_no_hash'), table_name='users')
    op.drop_column('users', 'id_no_hash')
