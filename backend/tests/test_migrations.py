import os
import tempfile
from pathlib import Path
import sqlalchemy
from alembic.config import Config
from alembic import command


def test_alembic_migrations_on_temporary_database():
    """
    Tests full upgrade to head and downgrade to base on an isolated temporary SQLite database.
    Guarantees that:
    1. Alembic migrations run cleanly without errors.
    2. Real database (celebration_planner.db) is NOT touched or overwritten.
    3. Both initial schema and ownership migrations succeed.
    """
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_migration_sandbox.db")
    temp_db_url = f"sqlite:///{temp_db_path}"

    root_dir = Path(__file__).resolve().parent.parent.parent
    ini_path = root_dir / "alembic.ini"
    assert ini_path.exists(), "alembic.ini must exist in project root"

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", temp_db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 2. Verify all tables exist
    engine = sqlalchemy.create_engine(temp_db_url)
    inspector = sqlalchemy.inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        "events",
        "users",
        "expenses",
        "guests",
        "invitations",
        "vendor_directory",
        "event_vendor_bookings",
        "chat_messages",
        "event_weather_plans",
    ]
    for tbl in expected_tables:
        assert tbl in tables, f"Expected table '{tbl}' was not created by migrations."

    # 3. Verify owner_id exists on events
    events_cols = [c["name"] for c in inspector.get_columns("events")]
    assert "owner_id" in events_cols, "Column 'owner_id' must exist on events table."

    # 4. Verify users table structure
    user_cols = [c["name"] for c in inspector.get_columns("users")]
    for col in ["id", "email", "hashed_password", "full_name", "is_active", "created_at"]:
        assert col in user_cols, f"Column '{col}' must exist on users table."

    # 5. Test downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = sqlalchemy.inspect(engine)
    remaining_tables = inspector.get_table_names()
    assert "events" not in remaining_tables, "Events table should be dropped after downgrade."
    assert "users" not in remaining_tables, "Users table should be dropped after downgrade."

    # Cleanup temp db
    engine.dispose()
    try:
        os.remove(temp_db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass
