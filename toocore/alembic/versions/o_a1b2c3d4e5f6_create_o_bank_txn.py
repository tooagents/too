"""create o_bank_txn (business bank transactions / 流水账)

Revision ID: o_a1b2c3d4e5f6
Revises: 49c230c45d8c
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'o_a1b2c3d4e5f6'
down_revision: Union[str, None] = '49c230c45d8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'o_bank_txn',
        # BaseMixin columns
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ten_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('biz_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('usr_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('cli_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('created_by', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('usr_type', sa.String(length=32), nullable=True),
        sa.Column('b_int', sa.Integer(), nullable=True),
        sa.Column('b_str', sa.String(), nullable=True),
        sa.Column('b_decimal', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('b_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('b_bool', sa.Boolean(), nullable=True),
        sa.Column('b_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('is_flag', sa.Boolean(), nullable=True),
        sa.Column('locale', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # o_bank_txn specific columns
        sa.Column('txn_date', sa.Date(), nullable=True),
        sa.Column('debit', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('credit', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('balance', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('source', sa.String(length=32), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        schema='too_acc',
    )

    op.create_index(op.f('ix_too_acc_o_bank_txn_id'), 'o_bank_txn', ['id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_o_bank_txn_ten_id'), 'o_bank_txn', ['ten_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_o_bank_txn_biz_id'), 'o_bank_txn', ['biz_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_o_bank_txn_usr_id'), 'o_bank_txn', ['usr_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_o_bank_txn_cli_id'), 'o_bank_txn', ['cli_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_o_bank_txn_created_by'), 'o_bank_txn', ['created_by'], unique=False, schema='too_acc')


def downgrade() -> None:
    op.drop_index(op.f('ix_too_acc_o_bank_txn_created_by'), table_name='o_bank_txn', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_o_bank_txn_cli_id'), table_name='o_bank_txn', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_o_bank_txn_usr_id'), table_name='o_bank_txn', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_o_bank_txn_biz_id'), table_name='o_bank_txn', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_o_bank_txn_ten_id'), table_name='o_bank_txn', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_o_bank_txn_id'), table_name='o_bank_txn', schema='too_acc')
    op.drop_table('o_bank_txn', schema='too_acc')
