"""create znote (notes stored in too_global)

Revision ID: z_e5f6a7b8c9d0
Revises: o_d4e5f6a7b8c9
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'z_e5f6a7b8c9d0'
down_revision: Union[str, None] = 'o_d4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'znote',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ten_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('biz_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('usr_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('cli_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('created_by', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('usr_type', sa.String(length=32), nullable=True),
        sa.Column('b_int', sa.Integer(), nullable=True),
        sa.Column('b_str', sa.String(), nullable=True),
        sa.Column('b_decimal', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('b_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('b_bool', sa.Boolean(), nullable=True),
        sa.Column('b_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('is_flag', sa.Boolean(), nullable=True),
        sa.Column('locale', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Note-specific columns
        sa.Column('note_title', sa.String(), nullable=True),
        sa.Column('note_color', sa.String(length=32), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        schema='too_global',
    )

    op.create_index(op.f('ix_too_global_znote_id'), 'znote', ['id'], unique=False, schema='too_global')
    op.create_index(op.f('ix_too_global_znote_ten_id'), 'znote', ['ten_id'], unique=False, schema='too_global')
    op.create_index(op.f('ix_too_global_znote_biz_id'), 'znote', ['biz_id'], unique=False, schema='too_global')
    op.create_index(op.f('ix_too_global_znote_usr_id'), 'znote', ['usr_id'], unique=False, schema='too_global')
    op.create_index(op.f('ix_too_global_znote_cli_id'), 'znote', ['cli_id'], unique=False, schema='too_global')
    op.create_index(op.f('ix_too_global_znote_created_by'), 'znote', ['created_by'], unique=False, schema='too_global')


def downgrade() -> None:
    op.drop_index(op.f('ix_too_global_znote_created_by'), table_name='znote', schema='too_global')
    op.drop_index(op.f('ix_too_global_znote_cli_id'), table_name='znote', schema='too_global')
    op.drop_index(op.f('ix_too_global_znote_usr_id'), table_name='znote', schema='too_global')
    op.drop_index(op.f('ix_too_global_znote_biz_id'), table_name='znote', schema='too_global')
    op.drop_index(op.f('ix_too_global_znote_ten_id'), table_name='znote', schema='too_global')
    op.drop_index(op.f('ix_too_global_znote_id'), table_name='znote', schema='too_global')

    op.drop_table('znote', schema='too_global')
