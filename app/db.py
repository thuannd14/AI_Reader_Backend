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
    """Ensure epoch-ms columns are BIGINT (Postgres INTEGER overflows ms timestamps).

    Verify information_schema; if columns are still int4, DROP + create_all so
    SQLModel BigInteger columns win. Learning-word rows are sync-rebuildable.
    """
    if "postgresql" not in DATABASE_URL and "postgres" not in DATABASE_URL:
        return
    # SQLModel default table name for LearningWord is "learningword".
    table = "learningword"

    def _epoch_columns_are_bigint(conn) -> bool:
        for column in ("added_at_epoch_ms", "updated_at_epoch_ms"):
            row = conn.execute(
                text(
                    """
                    SELECT udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table
                      AND column_name = :column
                    """
                ),
                {"table": table, "column": column},
            ).fetchone()
            if row is None:
                return False
            if (row[0] or "").lower() not in {"int8", "bigint"}:
                return False
        return True

    with engine.begin() as conn:
        if _epoch_columns_are_bigint(conn):
            return
        try:
            for column in ("added_at_epoch_ms", "updated_at_epoch_ms"):
                conn.execute(
                    text(
                        f"""
                        ALTER TABLE IF EXISTS {table}
                          ALTER COLUMN {column} TYPE BIGINT
                          USING {column}::bigint
                        """
                    )
                )
            if _epoch_columns_are_bigint(conn):
                return
        except Exception:
            pass
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    # create_all outside the DROP transaction so metadata sees a clean state.
    SQLModel.metadata.create_all(engine)



def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
