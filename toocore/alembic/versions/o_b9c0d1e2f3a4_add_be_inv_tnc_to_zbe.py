"""add be_inv_tnc to zbe (business-level default invoice terms & conditions)

Adds a business-level default for the invoice terms/late-payment footer:
  - too_global.zbe.be_inv_tnc — default T&C text used when an invoice has no
    inv_tnc of its own (render fallback: inv_tnc -> be_inv_tnc -> app default).

Revision ID: o_b9c0d1e2f3a4
Revises: o_a8b9c0d1e2f3
Create Date: 2026-09-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_b9c0d1e2f3a4'
down_revision: Union[str, None] = 'o_a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'zbe',
        sa.Column('be_inv_tnc', sa.String(length=1024), nullable=True),
        schema='too_global',
    )


def downgrade() -> None:
    op.drop_column('zbe', 'be_inv_tnc', schema='too_global')
