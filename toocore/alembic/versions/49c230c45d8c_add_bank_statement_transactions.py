"""add_bank_statement_transactions

Revision ID: 49c230c45d8c
Revises: 6951e07213b9
Create Date: 2026-06-28 09:42:52.474896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '49c230c45d8c'
down_revision: Union[str, None] = '6951e07213b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bank_statement_transactions table
    op.create_table(
        'bank_statement_transactions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ten_id', sa.UUID(), nullable=True),
        sa.Column('biz_id', sa.UUID(), nullable=True),
        sa.Column('usr_id', sa.UUID(), nullable=True),
        sa.Column('cli_id', sa.UUID(), nullable=True),
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
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Bank statement specific columns
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('account_name', sa.String(length=200), nullable=True),
        sa.Column('account_number', sa.String(length=50), nullable=True),
        sa.Column('statement_date', sa.Date(), nullable=True),
        sa.Column('statement_period', sa.String(length=50), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=True),
        sa.Column('debit_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('credit_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('balance', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('source_file_name', sa.String(length=255), nullable=True),
        sa.Column('row_number', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        schema='too_acc'
    )

    # Create indexes
    op.create_index(op.f('ix_too_acc_bank_statement_transactions_id'), 'bank_statement_transactions', ['id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_bank_statement_transactions_ten_id'), 'bank_statement_transactions', ['ten_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_bank_statement_transactions_biz_id'), 'bank_statement_transactions', ['biz_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_bank_statement_transactions_usr_id'), 'bank_statement_transactions', ['usr_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_bank_statement_transactions_cli_id'), 'bank_statement_transactions', ['cli_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_bank_statement_transactions_created_by'), 'bank_statement_transactions', ['created_by'], unique=False, schema='too_acc')


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_too_acc_bank_statement_transactions_created_by'), table_name='bank_statement_transactions', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_bank_statement_transactions_cli_id'), table_name='bank_statement_transactions', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_bank_statement_transactions_usr_id'), table_name='bank_statement_transactions', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_bank_statement_transactions_biz_id'), table_name='bank_statement_transactions', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_bank_statement_transactions_ten_id'), table_name='bank_statement_transactions', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_bank_statement_transactions_id'), table_name='bank_statement_transactions', schema='too_acc')

    # Drop table
    op.drop_table('bank_statement_transactions', schema='too_acc')
