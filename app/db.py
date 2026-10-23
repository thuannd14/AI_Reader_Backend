"""Database engine and session helpers."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


def init_db() -> None:
    """Create tables if they do not exist, then apply light schema fixes."""
    from . import models  # noqa: F401  (register models before create_all)

    SQLModel.metadata.create_all(engine)
    _migrate_learning_word_epoch_columns()


def _migrate_learning_word_epoch_columns() -> None:
    """Ensure epoch-ms columns are BIGINT (Postgres INTEGER overflows ms timestamps)."""
    if "postgresql" not in DATABASE_URL and "postgres" not in DATABASE_URL:
        return
    # SQLModel default table name for LearningWord is "learningword".
    statements = (
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'learningword'
          ) THEN
            ALTER TABLE learningword
              ALTER COLUMN added_at_epoch_ms TYPE BIGINT
              USING added_at_epoch_ms::bigint;
            ALTER TABLE learningword
              ALTER COLUMN updated_at_epoch_ms TYPE BIGINT
              USING updated_at_epoch_ms::bigint;
          END IF;
        END $$;
        """,
    )
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))



def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
