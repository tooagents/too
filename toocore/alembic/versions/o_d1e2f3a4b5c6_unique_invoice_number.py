"""enforce unique invoice number per tenant (partial unique index)

Invoice numbers must be unique within a tenant. This is a PARTIAL unique index so:
  - soft-deleted rows are excluded (is_deleted IS NOT TRUE) — a deleted invoice's
    number can be reused rather than being reserved forever.
  - NULL numbers are excluded — unnumbered rows (e.g. imported/agent-created) don't
    collide with each other. Blank strings are rejected upstream in the editor, so
    unnumbered rows should be stored as NULL, never ''.

Scope is (ten_id, inv_number): two different tenants may share a number.

NOTE: if existing data already has duplicate (ten_id, inv_number) among live rows,
index creation will fail — de-duplicate those first, then re-run.

Revision ID: o_d1e2f3a4b5c6
Revises: o_c0d1e2f3a4b5
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_d1e2f3a4b5c6'
down_revision: Union[str, None] = 'o_c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_too_inv_invoice_ten_number',
        'invoice',
        ['ten_id', 'inv_number'],
        unique=True,
        schema='too_inv',
        postgresql_where=sa.text('is_deleted IS NOT TRUE AND inv_number IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_too_inv_invoice_ten_number', table_name='invoice', schema='too_inv')
