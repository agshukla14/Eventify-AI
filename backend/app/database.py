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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
