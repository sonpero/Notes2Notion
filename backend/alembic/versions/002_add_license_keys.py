"""Add license_keys table

Revision ID: 002
Revises: 001
Create Date: 2025-01-28 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create license_keys table
    op.create_table(
        'license_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('used_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['used_by_user_id'], ['users.id'], ondelete='SET NULL')
    )

    # Create indexes
    op.create_index('ix_license_keys_key', 'license_keys', ['key'], unique=True)
    op.create_index('ix_license_keys_used_by_user_id', 'license_keys', ['used_by_user_id'])


def downgrade() -> None:
    # Drop indexes and table
    op.drop_index('ix_license_keys_used_by_user_id', table_name='license_keys')
    op.drop_index('ix_license_keys_key', table_name='license_keys')
    op.drop_table('license_keys')
