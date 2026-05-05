from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # reconnect on stale connections
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_call_reports_schema() -> None:
    """
    Add newly introduced columns to an existing call_reports table.

    Base.metadata.create_all() only creates missing tables; it does not mutate
    tables that already exist, so older deployments need a small schema sync.
    """
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    if "call_reports" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("call_reports")}
    required_columns = {
        "success_evaluation": "VARCHAR(20)",
        "structured_data": "JSON",
        "phone_number": "VARCHAR(50)",
        "caller_name": "VARCHAR(200)",
        "sentiment": "VARCHAR(50)",
        "reason_for_call": "TEXT",
        "transfer_successful": "BOOLEAN",
        "transfer_destination": "VARCHAR(100)",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                text(f'ALTER TABLE call_reports ADD COLUMN "{column_name}" {column_type}')
            )


def get_db():
    """FastAPI dependency that provides a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
