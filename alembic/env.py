import os
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.database import Base, db_connection_url
import backend.app.models  # ensure all models are registered

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use explicit sqlalchemy.url from config if provided (e.g. In tests or custom runs);
# otherwise fallback to DATABASE_URL environment or database connection URL.
current_url = config.get_main_option("sqlalchemy.url")
if not current_url or "driver://user:pass" in current_url:
    configured_url = os.getenv("DATABASE_URL", db_connection_url)
    if configured_url.startswith("postgres://"):
        configured_url = configured_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", configured_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
