"""add_users_and_ownership

Revision ID: 002_add_users_and_ownership
Revises: 001_initial_schema
Create Date: 2026-10-31

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_users_and_ownership'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. Add owner_id to events table via batch operations for cross-database (SQLite & PostgreSQL) compatibility
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_events_owner_id', ['owner_id'], unique=False)
        batch_op.create_foreign_key('fk_events_owner_id_users', 'users', ['owner_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint('fk_events_owner_id_users', type_='foreignkey')
        batch_op.drop_index('ix_events_owner_id')
        batch_op.drop_column('owner_id')

    op.drop_table('users')
