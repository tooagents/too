"""create ocr_documents (raw OCR JSON from Gemini)

Revision ID: o_c3d4e5f6a7b8
Revises: o_b2c3d4e5f6a7
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'o_c3d4e5f6a7b8'
down_revision: Union[str, None] = 'o_b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ocr_documents',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ten_id', sa.UUID(), nullable=True),
        sa.Column('biz_id', sa.UUID(), nullable=True),
        sa.Column('usr_id', sa.UUID(), nullable=True),
        sa.Column('cli_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=True),
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

        # OCR-specific columns
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('model_id', sa.String(length=100), nullable=True),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        schema='too_acc'
    )

    op.create_index(op.f('ix_too_acc_ocr_documents_id'), 'ocr_documents', ['id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_ocr_documents_ten_id'), 'ocr_documents', ['ten_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_ocr_documents_biz_id'), 'ocr_documents', ['biz_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_ocr_documents_usr_id'), 'ocr_documents', ['usr_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_ocr_documents_cli_id'), 'ocr_documents', ['cli_id'], unique=False, schema='too_acc')
    op.create_index(op.f('ix_too_acc_ocr_documents_created_by'), 'ocr_documents', ['created_by'], unique=False, schema='too_acc')


def downgrade() -> None:
    op.drop_index(op.f('ix_too_acc_ocr_documents_created_by'), table_name='ocr_documents', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_ocr_documents_cli_id'), table_name='ocr_documents', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_ocr_documents_usr_id'), table_name='ocr_documents', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_ocr_documents_biz_id'), table_name='ocr_documents', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_ocr_documents_ten_id'), table_name='ocr_documents', schema='too_acc')
    op.drop_index(op.f('ix_too_acc_ocr_documents_id'), table_name='ocr_documents', schema='too_acc')

    op.drop_table('ocr_documents', schema='too_acc')
