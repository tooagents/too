"""capitalize journal line type

Revision ID: f4b7c9e2a1d3
Revises: bcac990a0171
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f4b7c9e2a1d3"
down_revision: Union[str, None] = "bcac990a0171"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_journal_entry_lines_line_type",
        "journal_entry_lines",
        schema="too_acc",
        type_="check",
    )
    op.execute(
        """
        update too_acc.journal_entry_lines
        set line_type = case
            when line_type = 'debit' then 'Debit'
            when line_type = 'credit' then 'Credit'
            else line_type
        end
        where line_type in ('debit', 'credit')
        """
    )
    op.create_check_constraint(
        "ck_journal_entry_lines_line_type",
        "journal_entry_lines",
        "line_type in ('Debit','Credit')",
        schema="too_acc",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_journal_entry_lines_line_type",
        "journal_entry_lines",
        schema="too_acc",
        type_="check",
    )
    op.execute(
        """
        update too_acc.journal_entry_lines
        set line_type = case
            when line_type = 'Debit' then 'debit'
            when line_type = 'Credit' then 'credit'
            else line_type
        end
        where line_type in ('Debit', 'Credit')
        """
    )
    op.create_check_constraint(
        "ck_journal_entry_lines_line_type",
        "journal_entry_lines",
        "line_type in ('debit','credit')",
        schema="too_acc",
    )
