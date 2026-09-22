"""add be_default_tax_id to zbe (business-level default sales tax)

Adds a business-level default sales tax for new invoices:
  - too_global.zbe.be_default_tax_id — references too_inv.itax.id. When set, a
    new invoice seeds its tax label + rate from this preset; null keeps the
    prior behaviour (new invoices start with "No tax").

Revision ID: o_e1f2a3b4c5d6
Revises: o_d1e2f3a4b5c6
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_e1f2a3b4c5d6'
down_revision: Union[str, None] = 'o_d1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'zbe',
        sa.Column('be_default_tax_id', sa.Uuid(), nullable=True),
        schema='too_global',
    )


def downgrade() -> None:
    op.drop_column('zbe', 'be_default_tax_id', schema='too_global')
