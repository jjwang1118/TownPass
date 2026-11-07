"""prescriptions and ui alignment

依 UI 調整資料結構：
- 新增藥單（prescriptions），藥品改為掛在藥單底下（A1、A2）；吃藥時段改為固定四個，移除 time_slots
- 吃藥提醒改為長輩與家屬同時推播，移除再提醒與回應欄位
- 救命卡：姓名、出生年月日、血型；移除稱呼、出生年、常去醫院
- 救護人員查看紀錄加人員編號
- 回診：門診拆成看診時間（clinic_slots），各自有名額；預約改為自動前一天提醒
- 藥品資料加藥名搜尋用的欄位

medications、reminder_events、refill_notices 的選項（CHECK）都改了，所以整張重建；
門診與預約是模擬資料，後端啟動時 seed.load 會重新產生，所以清空。

Revision ID: f6497e343c3a
Revises: d4b4f0542791
Create Date: 2026-11-08 00:15:20.273856
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f6497e343c3a'
down_revision: str | None = 'd4b4f0542791'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def upgrade() -> None:
    # ---------- 藥：重建 ----------
    op.drop_table('reminder_events')
    op.drop_table('refill_notices')
    op.drop_table('medications')
    op.drop_table('time_slots')

    op.create_table('prescriptions',
    sa.Column('elder_id', sa.Uuid(), nullable=False),
    sa.Column('letter', sa.String(length=1), nullable=False),
    sa.Column('source', _enum('photo', 'qr', 'manual', name='prescriptionsource'), nullable=False),
    sa.Column('hospital', sa.String(length=64), nullable=True),
    sa.Column('department', sa.String(length=64), nullable=True),
    sa.Column('doctor', sa.String(length=64), nullable=True),
    sa.Column('visit_date', sa.Date(), nullable=False),
    sa.Column('days', sa.Integer(), nullable=False),
    sa.Column('status', _enum('active', 'finished', name='prescriptionstatus'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_prescriptions_created_by_users')),
    sa.ForeignKeyConstraint(['elder_id'], ['users.id'], name=op.f('fk_prescriptions_elder_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_prescriptions'))
    )
    op.create_index(op.f('ix_prescriptions_elder_id'), 'prescriptions', ['elder_id'], unique=False)
    op.create_index('uq_prescriptions_active_letter', 'prescriptions', ['elder_id', 'letter'], unique=True, postgresql_where=sa.text("status = 'active'"))

    op.create_table('medications',
    sa.Column('prescription_id', sa.Uuid(), nullable=False),
    sa.Column('elder_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('license_no', sa.String(length=64), nullable=True),
    sa.Column('strength', sa.String(length=32), nullable=True),
    sa.Column('purpose', sa.String(length=128), nullable=True),
    sa.Column('dose_qty', sa.Numeric(precision=3, scale=1), nullable=False),
    sa.Column('slots', sa.ARRAY(sa.String(length=16)), nullable=False),
    sa.Column('meal_timing', _enum('before', 'after', name='mealtiming'), nullable=False),
    sa.Column('needs_review', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('status', _enum('active', 'stopped', name='medicationstatus'), nullable=False),
    sa.Column('stopped_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('stop_reason', _enum('finished', 'doctor_advised', name='stopreason'), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['elder_id'], ['users.id'], name=op.f('fk_medications_elder_id_users')),
    sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], name=op.f('fk_medications_prescription_id_prescriptions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_medications')),
    sa.UniqueConstraint('prescription_id', 'seq', name=op.f('uq_medications_prescription_id'))
    )
    op.create_index(op.f('ix_medications_elder_id'), 'medications', ['elder_id'], unique=False)
    op.create_index(op.f('ix_medications_prescription_id'), 'medications', ['prescription_id'], unique=False)

    op.create_table('reminder_events',
    sa.Column('elder_id', sa.Uuid(), nullable=False),
    sa.Column('slot_key', _enum('morning', 'noon', 'evening', 'bedtime', name='slotkey'), nullable=False),
    sa.Column('scheduled_date', sa.Date(), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('groups', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('pushed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['elder_id'], ['users.id'], name=op.f('fk_reminder_events_elder_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reminder_events')),
    sa.UniqueConstraint('elder_id', 'slot_key', 'scheduled_date', name=op.f('uq_reminder_events_elder_id'))
    )
    op.create_index(op.f('ix_reminder_events_elder_id'), 'reminder_events', ['elder_id'], unique=False)
    op.create_index(op.f('ix_reminder_events_scheduled_at'), 'reminder_events', ['scheduled_at'], unique=False)

    op.create_table('refill_notices',
    sa.Column('elder_id', sa.Uuid(), nullable=False),
    sa.Column('run_out_date', sa.Date(), nullable=False),
    sa.Column('letters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['elder_id'], ['users.id'], name=op.f('fk_refill_notices_elder_id_users')),
    sa.PrimaryKeyConstraint('elder_id', 'run_out_date', name=op.f('pk_refill_notices'))
    )

    # ---------- 藥品資料：藥名搜尋用的欄位 ----------
    op.add_column('drug_licenses', sa.Column('product_en', sa.String(length=256), nullable=True))
    op.add_column('drug_licenses', sa.Column('product_zh', sa.String(length=256), nullable=True))
    op.add_column('drug_licenses', sa.Column('ingredient_en', sa.String(length=256), nullable=True))
    op.add_column('drug_licenses', sa.Column('strength', sa.String(length=32), nullable=True))
    op.add_column('drug_licenses', sa.Column('form', sa.String(length=32), nullable=True))
    op.create_index(op.f('ix_drug_licenses_product_en'), 'drug_licenses', ['product_en'], unique=False)

    # ---------- 救命卡 ----------
    op.add_column('emergency_cards', sa.Column('name', sa.Text(), nullable=True))
    op.add_column('emergency_cards', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('emergency_cards', sa.Column('blood_type', sa.String(length=32), server_default='unknown', nullable=False))
    op.create_check_constraint(
        op.f('ck_emergency_cards_bloodtype'), 'emergency_cards', "blood_type IN ('A', 'B', 'O', 'AB', 'unknown')"
    )
    # 舊資料沒有姓名：先用稱呼。稱呼原本不加密，之後長輩儲存救命卡時會以加密格式重新寫入
    op.execute("UPDATE emergency_cards SET name = title")
    op.alter_column('emergency_cards', 'name', nullable=False)
    op.drop_column('emergency_cards', 'title')
    op.drop_column('emergency_cards', 'birth_year')
    op.drop_column('emergency_cards', 'hospital')
    op.add_column('card_access_logs', sa.Column('responder_staff_no', sa.String(length=32), nullable=True))

    # ---------- 回診：看診時間與名額 ----------
    op.execute("DELETE FROM appointments")
    op.execute("DELETE FROM clinic_sessions")
    op.drop_column('clinic_sessions', 'booked_count')
    op.drop_column('clinic_sessions', 'capacity')
    op.create_table('clinic_slots',
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('time', sa.Time(), nullable=False),
    sa.Column('capacity', sa.SmallInteger(), nullable=False),
    sa.Column('booked_count', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['clinic_sessions.id'], name=op.f('fk_clinic_slots_session_id_clinic_sessions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinic_slots')),
    sa.UniqueConstraint('session_id', 'time', name=op.f('uq_clinic_slots_session_id'))
    )
    op.create_index(op.f('ix_clinic_slots_session_id'), 'clinic_slots', ['session_id'], unique=False)
    op.add_column('appointments', sa.Column('slot_id', sa.Uuid(), nullable=False))
    op.create_index(op.f('ix_appointments_slot_id'), 'appointments', ['slot_id'], unique=False)
    op.create_foreign_key(op.f('fk_appointments_slot_id_clinic_slots'), 'appointments', 'clinic_slots', ['slot_id'], ['id'])
    op.drop_column('appointments', 'reminded_same_day_at')
    op.drop_column('appointments', 'reminder_enabled')


def downgrade() -> None:
    raise NotImplementedError(
        "這一版大幅調整藥品與提醒的資料結構，無法降版。請用 docker compose down -v 清空資料庫後，切回舊版重新建立。"
    )
