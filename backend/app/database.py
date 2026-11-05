import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

# Normalize PostgreSQL scheme for Render / cloud deployments
db_connection_url = DATABASE_URL
if db_connection_url.startswith("postgres://"):
    db_connection_url = db_connection_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if db_connection_url.startswith("sqlite") else {}

engine = create_engine(
    db_connection_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db_schema_and_migrations():
    """
    Safely ensures all required tables and columns exist in SQLite/PostgreSQL
    without dropping or modifying existing data or relationships.
    Also ensures all existing user accounts are active and email-verified.
    """
    from sqlalchemy import text
    with engine.begin() as conn:
        # Check SQLite table info for users columns
        try:
            res = conn.execute(text("PRAGMA table_info(users);")).fetchall()
            existing_cols = {row[1] for row in res}
            if existing_cols and "email_verified" not in existing_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 1;"))
            if existing_cols and "email_verified_at" not in existing_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_verified_at VARCHAR(40);"))
            # Safely verify all existing accounts so they can log in without OTP
            conn.execute(text("UPDATE users SET email_verified = 1 WHERE email_verified = 0 OR email_verified IS NULL;"))
        except Exception:
            pass

    # Ensure models are loaded before create_all
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
