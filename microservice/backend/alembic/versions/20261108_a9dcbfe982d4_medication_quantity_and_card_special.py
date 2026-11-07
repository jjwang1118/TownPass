"""medication quantity and card special

藥品新增總顆數（還剩幾天 = 剩下顆數 ÷ 每天吃幾顆，和前端相同），藥單天數改為選填；
救命卡新增特殊狀況（加密）與慣用語言。

Revision ID: a9dcbfe982d4
Revises: f6497e343c3a
Create Date: 2026-11-08 01:06:19.675879
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a9dcbfe982d4'
down_revision: str | None = 'f6497e343c3a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('emergency_cards', sa.Column('special', sa.Text(), nullable=True))
    op.add_column('emergency_cards', sa.Column('language', sa.String(length=8), nullable=True))
    op.add_column('medications', sa.Column('quantity', sa.Numeric(precision=6, scale=1), nullable=True))
    op.alter_column('prescriptions', 'days',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('prescriptions', 'days',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('medications', 'quantity')
    op.drop_column('emergency_cards', 'language')
    op.drop_column('emergency_cards', 'special')
