"""add is_reconciled to o_bank_txn (binary deposit-level reconcile flag)

Reconcile is a yes/no workflow state of the deposit (True only when fully applied;
partial stays False). The invoice links/amounts still live in invoice_payment; this
column is just the flag. Existing fully-applied deposits are backfilled to true.

Revision ID: o_f7a8b9c0d1e2
Revises: o_e6f7a8b9c0d1
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_f7a8b9c0d1e2'
down_revision: Union[str, None] = 'o_e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'o_bank_txn',
        sa.Column('is_reconciled', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        schema='too_acc',
    )
    # Backfill: a deposit already fully applied to invoices is reconciled.
    op.execute(
        """
        UPDATE too_acc.o_bank_txn b
        SET is_reconciled = true
        WHERE b.is_deleted IS NOT TRUE
          AND b.credit IS NOT NULL AND b.credit > 0
          AND COALESCE((
                SELECT SUM(p.pay_amount) FROM too_inv.invoice_payment p
                WHERE p.bank_txn_id = b.id AND p.is_deleted IS NOT TRUE
          ), 0) >= b.credit
        """
    )


def downgrade() -> None:
    op.drop_column('o_bank_txn', 'is_reconciled', schema='too_acc')
