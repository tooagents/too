"""add client_inv_term to zclient (client-level default invoice terms)

Adds a per-client default for the invoice terms/late-payment footer:
  - too_global.zclient.client_inv_term — the client's default footer terms,
    copied onto new invoices as inv_tnc. Distinct from client_terms_conditions
    (the short payment-terms label, e.g. "Net 7").

Render fallback stays: invoice inv_tnc -> business be_inv_tnc -> app default.

Revision ID: o_c0d1e2f3a4b5
Revises: o_b9c0d1e2f3a4
Create Date: 2026-09-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_c0d1e2f3a4b5'
down_revision: Union[str, None] = 'o_b9c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'zclient',
        sa.Column('client_inv_term', sa.String(length=255), nullable=True),
        schema='too_global',
    )


def downgrade() -> None:
    op.drop_column('zclient', 'client_inv_term', schema='too_global')
