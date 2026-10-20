"""Application configuration (env-driven)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite by default; set DATABASE_URL to switch to PostgreSQL/MySQL, e.g.
#   postgresql+psycopg://user:pass@host:5432/dbname
# Railway/Render often inject postgres:// or postgresql:// — normalize for psycopg3.
DEFAULT_DB_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


DATABASE_URL = _normalize_database_url(
    os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
)

API_TITLE = "AI Reader Vocabulary API"
API_VERSION = "1.0.0"

# --- Authentication -------------------------------------------------------
# Comma-separated list of accepted API keys. If empty, auth is DISABLED
# (convenient for local development). Set it in production:
#   API_KEYS=key_one,key_two
_raw_keys = os.environ.get("API_KEYS", "").strip()
API_KEYS: set[str] = {k.strip() for k in _raw_keys.split(",") if k.strip()}
AUTH_ENABLED: bool = bool(API_KEYS)

