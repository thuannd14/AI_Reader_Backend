"""API smoke tests (uses a throwaway SQLite database)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Point the app at a temporary database BEFORE importing it.
_TMP_DB = Path(tempfile.gettempdir()) / "aireader_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

EN_CSV = (
    "word,level,pos,ipa,definition_en,meaning_vi,example,count\n"
    "compensate,B2,verb,ˈkɑːmpenseɪt,to make up for,bù đắp,compensate for delays,3\n"
    "absorb,B1,verb,əbˈzɔːrb,to take in,hấp thụ,rain gardens absorb water,5\n"
)

ZH_CSV = (
    "word,traditional,level,pos,ipa,definition_en,meaning_vi,example,count\n"
    "提高,提高,HSK3,v,tí gāo,to raise,nâng cao,我们要提高生产力,4\n"
)


def main() -> int:
    init_db()
    client = TestClient(app)

    # health
    assert client.get("/health").json()["status"] == "ok"

    # import English + Chinese
    en = client.post(
        "/import",
        files={"file": ("en.csv", EN_CSV, "text/csv")},
        data={"source_name": "en_doc"},
    ).json()
    assert en["language"] == "en" and en["imported"] == 2, en

    zh = client.post(
        "/import",
        files={"file": ("zh.csv", ZH_CSV, "text/csv")},
        data={"source_name": "zh_doc", "language": "zh", "level": "HSK3"},
    ).json()
    assert zh["language"] == "zh" and zh["imported"] == 1, zh

    # list + filters
    all_words = client.get("/words").json()
    assert all_words["total"] == 3, all_words

    zh_only = client.get("/words", params={"lang": "zh"}).json()
    assert zh_only["total"] == 1 and zh_only["items"][0]["word"] == "提高", zh_only

    search = client.get("/words", params={"q": "absorb"}).json()
    assert search["total"] == 1, search

    level = client.get("/words", params={"level": "B2"}).json()
    assert level["total"] == 1 and level["items"][0]["word"] == "compensate", level

    # single word + 404
    word_id = all_words["items"][0]["id"]
    assert client.get(f"/words/{word_id}").status_code == 200
    assert client.get("/words/999999").status_code == 404

    # sources + stats
    sources = client.get("/sources").json()
    assert {s["name"] for s in sources} == {"en_doc", "zh_doc"}, sources
    stats = client.get("/stats").json()
    assert stats["total_words"] == 3 and stats["languages"] == {"en": 2, "zh": 1}, stats

    # idempotent re-import replaces without duplicating
    client.post(
        "/import",
        files={"file": ("en.csv", EN_CSV, "text/csv")},
        data={"source_name": "en_doc"},
    )
    assert client.get("/words").json()["total"] == 3

    # export as a downloadable JSON file
    export = client.get("/export", params={"lang": "en"})
    assert export.status_code == 200
    assert "attachment" in export.headers.get("content-disposition", "")
    assert export.json()["count"] == 2, export.json()

    print("ALL API TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
