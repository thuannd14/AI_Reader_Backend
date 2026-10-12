"""Application configuration (env-driven)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite by default; set DATABASE_URL to switch to PostgreSQL/MySQL, e.g.
#   postgresql+psycopg://user:pass@host:5432/dbname
DEFAULT_DB_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

API_TITLE = "AI Reader Vocabulary API"
API_VERSION = "1.0.0"
