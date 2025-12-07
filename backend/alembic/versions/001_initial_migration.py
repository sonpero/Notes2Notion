"""Initial migration - create users table

Revision ID: 001
Revises:
Create Date: 2025-01-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bot_id', sa.String(length=255), nullable=False),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('workspace_name', sa.String(length=500), nullable=True),
        sa.Column('access_token', sa.String(length=1000), nullable=False),
        sa.Column('refresh_token', sa.String(length=1000), nullable=True),
        sa.Column('notion_page_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Create index on bot_id (it's unique and frequently queried)
    op.create_index(op.f('ix_users_bot_id'), 'users', ['bot_id'], unique=True)


def downgrade() -> None:
    # Drop index and table
    op.drop_index(op.f('ix_users_bot_id'), table_name='users')
    op.drop_table('users')
