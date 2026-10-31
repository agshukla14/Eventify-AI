"""initial_schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-31

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Events Table
    op.create_table(
        'events',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('date', sa.String(length=20), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('guest_count', sa.Integer(), nullable=False),
        sa.Column('total_budget', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR'),
        sa.Column('intake_json', sa.Text(), nullable=False),
        sa.Column('plan_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_events_id', 'events', ['id'], unique=False)

    # 2. Expenses Table
    op.create_table(
        'expenses',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('event_id', sa.String(length=64), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expense_name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('expense_date', sa.String(length=20), nullable=False),
        sa.Column('payment_status', sa.String(length=20), server_default='Paid', nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('vendor_name', sa.String(length=150), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_expenses_id', 'expenses', ['id'], unique=False)
    op.create_index('ix_expenses_event_id', 'expenses', ['event_id'], unique=False)
    op.create_index('ix_expenses_category', 'expenses', ['category'], unique=False)
    op.create_index('ix_expenses_expense_date', 'expenses', ['expense_date'], unique=False)

    # 3. Guests Table
    op.create_table(
        'guests',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('event_id', sa.String(length=64), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), server_default='Others', nullable=False),
        sa.Column('plus_ones', sa.Integer(), server_default='0', nullable=False),
        sa.Column('invitation_status', sa.String(length=20), server_default='Not Sent', nullable=False),
        sa.Column('rsvp_status', sa.String(length=20), server_default='Pending', nullable=False),
        sa.Column('special_requirements', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_guests_id', 'guests', ['id'], unique=False)
    op.create_index('ix_guests_event_id', 'guests', ['event_id'], unique=False)
    op.create_index('ix_guests_full_name', 'guests', ['full_name'], unique=False)
    op.create_index('ix_guests_rsvp_status', 'guests', ['rsvp_status'], unique=False)

    # 4. Invitations Table
    op.create_table(
        'invitations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('event_id', sa.String(length=64), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('guest_id', sa.String(length=64), sa.ForeignKey('guests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('language', sa.String(length=50), server_default='English', nullable=False),
        sa.Column('style', sa.String(length=50), server_default='Traditional', nullable=False),
        sa.Column('template_id', sa.String(length=50), server_default='traditional_indian_wedding', nullable=False),
        sa.Column('invitation_text_json', sa.Text(), nullable=False),
        sa.Column('design_config_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_invitations_id', 'invitations', ['id'], unique=False)
    op.create_index('ix_invitations_event_id', 'invitations', ['event_id'], unique=False)

    # 5. Vendor Directory Table
    op.create_table(
        'vendor_directory',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('services_offered', sa.Text(), nullable=False),
        sa.Column('min_price', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('max_price', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rating', sa.Float(), server_default='5.0', nullable=False),
        sa.Column('review_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('experience_years', sa.Integer(), server_default='1', nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('portfolio_images', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('is_favorite', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_vendor_directory_id', 'vendor_directory', ['id'], unique=False)
    op.create_index('ix_vendor_directory_name', 'vendor_directory', ['name'], unique=False)
    op.create_index('ix_vendor_directory_category', 'vendor_directory', ['category'], unique=False)
    op.create_index('ix_vendor_directory_location', 'vendor_directory', ['location'], unique=False)

    # 6. Event Vendor Bookings Table
    op.create_table(
        'event_vendor_bookings',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('event_id', sa.String(length=64), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vendor_id', sa.String(length=64), sa.ForeignKey('vendor_directory.id', ondelete='CASCADE'), nullable=False),
        sa.Column('booking_status', sa.String(length=30), server_default='Shortlisted', nullable=False),
        sa.Column('agreed_price', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('advance_payment', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('booking_date', sa.String(length=40), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
        sa.UniqueConstraint('event_id', 'vendor_id', name='uq_event_vendor'),
    )
    op.create_index('ix_event_vendor_bookings_id', 'event_vendor_bookings', ['id'], unique=False)
    op.create_index('ix_event_vendor_bookings_event_id', 'event_vendor_bookings', ['event_id'], unique=False)

    # 7. Chat Messages Table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls_json', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)
    op.create_index('ix_chat_messages_event_id', 'chat_messages', ['event_id'], unique=False)

    # 8. Event Weather Plans Table
    op.create_table(
        'event_weather_plans',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('event_id', sa.String(length=64), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('location_name', sa.String(length=150), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('target_date', sa.String(length=20), nullable=False),
        sa.Column('data_type', sa.String(length=50), server_default='live_forecast', nullable=False),
        sa.Column('weather_summary_json', sa.Text(), nullable=False),
        sa.Column('saved_mitigations_json', sa.Text(), nullable=True),
        sa.Column('retrieved_at', sa.String(length=40), nullable=False),
        sa.Column('created_at', sa.String(length=40), nullable=False),
        sa.Column('updated_at', sa.String(length=40), nullable=False),
    )
    op.create_index('ix_event_weather_plans_id', 'event_weather_plans', ['id'], unique=False)
    op.create_index('ix_event_weather_plans_event_id', 'event_weather_plans', ['event_id'], unique=False)


def downgrade() -> None:
    op.drop_table('event_weather_plans')
    op.drop_table('chat_messages')
    op.drop_table('event_vendor_bookings')
    op.drop_table('vendor_directory')
    op.drop_table('invitations')
    op.drop_table('guests')
    op.drop_table('expenses')
    op.drop_table('events')
