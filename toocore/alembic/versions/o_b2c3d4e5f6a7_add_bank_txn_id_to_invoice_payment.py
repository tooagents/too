"""add bank_txn_id to invoice_payment (bank deposit -> invoice payment link)

Revision ID: o_b2c3d4e5f6a7
Revises: o_a1b2c3d4e5f6
Create Date: 2026-08-08 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_b2c3d4e5f6a7'
down_revision: Union[str, None] = 'o_a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'invoice_payment',
        sa.Column('bank_txn_id', sa.UUID(), nullable=True),
        schema='too_inv',
    )
    op.create_index(
        op.f('ix_too_inv_invoice_payment_bank_txn_id'),
        'invoice_payment',
        ['bank_txn_id'],
        unique=False,
        schema='too_inv',
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_too_inv_invoice_payment_bank_txn_id'),
        table_name='invoice_payment',
        schema='too_inv',
    )
    op.drop_column('invoice_payment', 'bank_txn_id', schema='too_inv')
