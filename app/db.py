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

    Learning-word rows are sync-rebuildable from the app, so we prefer a clean
    recreate whenever the live columns are not int8.
    """
    if "postgresql" not in DATABASE_URL and "postgres" not in DATABASE_URL:
        return
    # SQLModel default table name for LearningWord is "learningword".
    table = "learningword"

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table
                  AND column_name IN ('added_at_epoch_ms', 'updated_at_epoch_ms')
                """
            ),
            {"table": table},
        ).fetchall()
        by_name = {r[0]: (r[1] or "").lower() for r in rows}
        ok = (
            by_name.get("added_at_epoch_ms") in {"int8", "bigint"}
            and by_name.get("updated_at_epoch_ms") in {"int8", "bigint"}
        )
        if ok:
            return
        # Nuclear: drop stale INTEGER table so create_all applies BigInteger.
        for name in (table, "learning_word", "learning_words"):
            conn.execute(text(f"DROP TABLE IF EXISTS {name} CASCADE"))

    SQLModel.metadata.create_all(engine)



def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
