"""add reconciliation to invoice (invoice-level bank_txn link + is_reconciled)

Reconciliation is a first-class bank_txn <-> invoice link that lives on the invoice
and IS the source of truth (payments become side-work). This adds:
  - too_inv.invoice.is_reconciled          — explicit yes/no reconcile flag
  - too_inv.invoice.reconciled_bank_txn_id — the deposit this invoice is reconciled to

Backfill: existing reconciliations live only in invoice_payment.bank_txn_id today, so
flag every invoice that has a bank-linked payment and point it at that deposit.

Revision ID: o_a8b9c0d1e2f3
Revises: o_f7a8b9c0d1e2
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_a8b9c0d1e2f3'
down_revision: Union[str, None] = 'o_f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'invoice',
        sa.Column('is_reconciled', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        schema='too_inv',
    )
    op.add_column(
        'invoice',
        sa.Column('reconciled_bank_txn_id', sa.Uuid(), nullable=True),
        schema='too_inv',
    )
    op.create_index(
        'ix_too_inv_invoice_reconciled_bank_txn_id',
        'invoice',
        ['reconciled_bank_txn_id'],
        schema='too_inv',
    )
    # Backfill from the existing payment-based links: an invoice with a bank-linked
    # payment is reconciled, against that payment's deposit (newest wins if several).
    op.execute(
        """
        UPDATE too_inv.invoice i
        SET is_reconciled = true,
            reconciled_bank_txn_id = sub.bank_txn_id
        FROM (
            SELECT DISTINCT ON (inv_id) inv_id, bank_txn_id
            FROM too_inv.invoice_payment
            WHERE bank_txn_id IS NOT NULL AND is_deleted IS NOT TRUE
            ORDER BY inv_id, created_at DESC
        ) sub
        WHERE i.id = sub.inv_id
        """
    )


def downgrade() -> None:
    op.drop_index('ix_too_inv_invoice_reconciled_bank_txn_id', table_name='invoice', schema='too_inv')
    op.drop_column('invoice', 'reconciled_bank_txn_id', schema='too_inv')
    op.drop_column('invoice', 'is_reconciled', schema='too_inv')
