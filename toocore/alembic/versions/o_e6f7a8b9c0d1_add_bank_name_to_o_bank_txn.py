"""add bank_name to o_bank_txn (which bank/account a row came from)

Only `bank_name` is new. The model stopped overriding BaseMixin's
`type`/`status`/`description`, but those columns still exist physically (the
create migration wrote them from the BaseMixin block) and the model still maps
them via BaseMixin, so no columns are dropped here.

Revision ID: o_e6f7a8b9c0d1
Revises: z_e5f6a7b8c9d0
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_e6f7a8b9c0d1'
down_revision: Union[str, None] = 'z_e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'o_bank_txn',
        sa.Column('bank_name', sa.String(length=128), nullable=True),
        schema='too_acc',
    )


def downgrade() -> None:
    op.drop_column('o_bank_txn', 'bank_name', schema='too_acc')
