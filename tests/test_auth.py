"""Authentication tests (run in a separate process with API_KEYS set)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP_DB = Path(tempfile.gettempdir()) / "aireader_auth_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["API_KEYS"] = "secret123,another-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import API_KEYS, AUTH_ENABLED  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


def main() -> int:
    assert AUTH_ENABLED and API_KEYS == {"secret123", "another-key"}, API_KEYS
    init_db()
    client = TestClient(app)

    # public endpoints
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200

    # protected without key
    assert client.get("/words").status_code == 401
    assert client.get("/stats").status_code == 401
    assert client.get("/sources").status_code == 401
    assert client.post(
        "/import", files={"file": ("x.csv", "word,level\nrun,A1\n", "text/csv")}
    ).status_code == 401

    # wrong key
    assert client.get("/words", headers={"X-API-Key": "wrong"}).status_code == 401

    # valid key via X-API-Key and via Bearer
    assert client.get("/words", headers={"X-API-Key": "secret123"}).status_code == 200
    assert client.get(
        "/words", headers={"Authorization": "Bearer another-key"}
    ).status_code == 200

    # import with key works
    assert client.post(
        "/import",
        headers={"X-API-Key": "secret123"},
        files={"file": ("x.csv", "word,level\nrun,A1\n", "text/csv")},
        data={"source_name": "auth_doc"},
    ).status_code == 200

    print("ALL AUTH TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
