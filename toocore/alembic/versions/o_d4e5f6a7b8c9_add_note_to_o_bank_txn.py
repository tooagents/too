"""add note to o_bank_txn (user free-text note)

The o_bank_txn model now owns explicit `type`/`status`/`note` columns instead of
borrowing BaseMixin's generics. `type` and `status` already exist physically (the
create migration wrote them from the BaseMixin block), so only `note` is new here.

Revision ID: o_d4e5f6a7b8c9
Revises: o_c3d4e5f6a7b8
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o_d4e5f6a7b8c9'
down_revision: Union[str, None] = 'o_c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'o_bank_txn',
        sa.Column('note', sa.Text(), nullable=True),
        schema='too_acc',
    )


def downgrade() -> None:
    op.drop_column('o_bank_txn', 'note', schema='too_acc')
