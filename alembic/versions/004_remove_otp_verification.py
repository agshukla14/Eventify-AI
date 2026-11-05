"""remove_otp_verification

Revision ID: 004_remove_otp_verification
Revises: 003_add_email_verification_and_otp
Create Date: 2026-11-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_remove_otp_verification'
down_revision: Union[str, None] = '003_add_email_verification_and_otp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure all existing users are marked verified so they can log in without OTP verification
    op.execute("UPDATE users SET email_verified = 1 WHERE email_verified = 0 OR email_verified IS NULL")


def downgrade() -> None:
    pass
