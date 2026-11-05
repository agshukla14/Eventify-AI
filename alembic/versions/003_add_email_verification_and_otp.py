"""add_email_verification_and_otp

Revision ID: 003_add_email_verification_and_otp
Revises: 002_add_users_and_ownership
Create Date: 2026-11-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_email_verification_and_otp'
down_revision: Union[str, None] = '002_add_users_and_ownership'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add email_verified & email_verified_at to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('email_verified_at', sa.String(length=40), nullable=True))

    # 2. Create email_otps table
    op.create_table(
        'email_otps',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('purpose', sa.String(length=40), server_default='email_verification', nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='5', nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_email_otps_id', 'email_otps', ['id'], unique=False)
    op.create_index('ix_email_otps_user_id', 'email_otps', ['user_id'], unique=False)
    op.create_index('ix_email_otps_email', 'email_otps', ['email'], unique=False)
    op.create_index('ix_email_otps_expires_at', 'email_otps', ['expires_at'], unique=False)
    op.create_index('ix_email_otps_is_used', 'email_otps', ['is_used'], unique=False)

    # 3. Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'], unique=False)
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'], unique=False)
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=False)
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'], unique=False)
    op.create_index('ix_password_reset_tokens_is_used', 'password_reset_tokens', ['is_used'], unique=False)


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
    op.drop_table('email_otps')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('email_verified_at')
        batch_op.drop_column('email_verified')

