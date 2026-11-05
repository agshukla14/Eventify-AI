from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=True)
    email_verified_at = Column(String(40), nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    events = relationship("EventModel", back_populates="owner", lazy="select")


class EventModel(Base):
    __tablename__ = "events"

    id = Column(String(64), primary_key=True, index=True)
    owner_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    title = Column(String(150), nullable=False)
    event_type = Column(String(50), nullable=False)
    date = Column(String(20), nullable=False)
    city = Column(String(100), nullable=False)
    guest_count = Column(Integer, nullable=False)
    total_budget = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    intake_json = Column(Text, nullable=False)
    plan_json = Column(Text, nullable=False)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    owner = relationship("UserModel", back_populates="events")
    expenses = relationship("ExpenseModel", back_populates="event", cascade="all, delete-orphan", lazy="select")
    guests = relationship("GuestModel", back_populates="event", cascade="all, delete-orphan", lazy="select")
    invitations = relationship("InvitationModel", back_populates="event", cascade="all, delete-orphan", lazy="select")
    vendor_bookings = relationship("EventVendorBookingModel", back_populates="event", cascade="all, delete-orphan", lazy="select")
    weather_plans = relationship("EventWeatherPlanModel", back_populates="event", cascade="all, delete-orphan", lazy="select")


class ExpenseModel(Base):
    __tablename__ = "expenses"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    expense_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    expense_date = Column(String(20), nullable=False, index=True)
    payment_status = Column(String(20), default="Paid", nullable=False)
    payment_method = Column(String(50), nullable=True)
    vendor_name = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    event = relationship("EventModel", back_populates="expenses")


class GuestModel(Base):
    __tablename__ = "guests"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    full_name = Column(String(150), nullable=False, index=True)
    email = Column(String(150), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    category = Column(String(50), nullable=False, default="Others", index=True)
    plus_ones = Column(Integer, nullable=False, default=0)
    invitation_status = Column(String(20), nullable=False, default="Not Sent", index=True)
    rsvp_status = Column(String(20), nullable=False, default="Pending", index=True)
    special_requirements = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    event = relationship("EventModel", back_populates="guests")
    invitations = relationship("InvitationModel", back_populates="guest", lazy="select")


class InvitationModel(Base):
    __tablename__ = "invitations"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    guest_id = Column(String(64), ForeignKey("guests.id", ondelete="SET NULL"), index=True, nullable=True)
    title = Column(String(200), nullable=False)
    language = Column(String(50), nullable=False, default="English", index=True)
    style = Column(String(50), nullable=False, default="Traditional", index=True)
    template_id = Column(String(50), nullable=False, default="traditional_indian_wedding")
    invitation_text_json = Column(Text, nullable=False)  # JSON: greeting, event_details, message, closing, full_text
    design_config_json = Column(Text, nullable=False)    # JSON: bg_theme, bg_color, text_color, accent_color, font_family, etc.
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    event = relationship("EventModel", back_populates="invitations")
    guest = relationship("GuestModel", back_populates="invitations")


class VendorDirectoryModel(Base):
    __tablename__ = "vendor_directory"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    location = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    services_offered = Column(Text, nullable=False)  # JSON array string
    min_price = Column(Float, nullable=False, default=0.0)
    max_price = Column(Float, nullable=False, default=0.0)
    rating = Column(Float, nullable=False, default=5.0)
    review_count = Column(Integer, nullable=False, default=0)
    experience_years = Column(Integer, nullable=False, default=1)
    phone = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    website = Column(String(255), nullable=True)
    portfolio_images = Column(Text, nullable=True)  # JSON array string
    is_verified = Column(Boolean, nullable=False, default=False, index=True)
    is_favorite = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    bookings = relationship("EventVendorBookingModel", back_populates="vendor", cascade="all, delete-orphan", lazy="select")


class EventVendorBookingModel(Base):
    __tablename__ = "event_vendor_bookings"
    __table_args__ = (
        UniqueConstraint("event_id", "vendor_id", name="uq_event_vendor"),
    )

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    vendor_id = Column(String(64), ForeignKey("vendor_directory.id", ondelete="CASCADE"), index=True, nullable=False)
    booking_status = Column(String(30), nullable=False, default="Shortlisted", index=True)
    agreed_price = Column(Float, nullable=False, default=0.0)
    advance_payment = Column(Float, nullable=False, default=0.0)
    booking_date = Column(String(40), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    event = relationship("EventModel", back_populates="vendor_bookings")
    vendor = relationship("VendorDirectoryModel", back_populates="bookings")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), index=True, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls_json = Column(Text, nullable=True)
    timestamp = Column(String(40), nullable=False)


class EventWeatherPlanModel(Base):
    __tablename__ = "event_weather_plans"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    location_name = Column(String(150), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    target_date = Column(String(20), nullable=False, index=True)
    data_type = Column(String(50), nullable=False, default="live_forecast")  # "live_forecast" or "historical_reference"
    weather_summary_json = Column(Text, nullable=False)
    saved_mitigations_json = Column(Text, nullable=True)  # JSON array of saved task titles
    retrieved_at = Column(String(40), nullable=False)
    created_at = Column(String(40), nullable=False)
    updated_at = Column(String(40), nullable=False)

    event = relationship("EventModel", back_populates="weather_plans")
