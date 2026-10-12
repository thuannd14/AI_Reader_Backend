# AI Reader — Vocabulary Backend API

Backend REST API that stores vocabulary extracted by the
[`AI_Reader_Document`](../AI_Reader_Document) tool and serves it to clients
(the Android app).

```
[docx/pdf] --(AI_Reader_Document tool)--> _vocab.csv
                                              |
                                    (import_vocab.py / POST /import)
                                              v
                                        [ SQLite/Postgres ]
                                              ^
                                          [ this API ]
                                              ^
                                    [ Android app (Retrofit) ]
```

## Stack

- **FastAPI** + **Uvicorn**
- **SQLModel** (SQLAlchemy + Pydantic)
- **SQLite** by default, switchable to PostgreSQL/MySQL via `DATABASE_URL`

## Install & run

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# or on Windows:
run.bat
```

- Interactive docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

## Run with Docker

```bash
docker compose up --build          # build + start at http://localhost:8000
docker compose logs -f api
docker compose down
```

- The SQLite file persists in `./data` (mounted volume).
- Healthcheck hits `/health` every 30s.
- **PostgreSQL:** uncomment the `db` service and the `DATABASE_URL` line in
  `docker-compose.yml`, then add the driver to the image
  (`pip install -r requirements-postgres.txt`) and rebuild.

Import CSV inside the running container:

```bash
docker compose exec api python -m scripts.import_vocab /data/sample.csv --source "Sample" --lang en
```

## Import vocabulary

The tool writes a CSV with a fixed schema
(`word, [traditional], level, pos, ipa, definition_en, meaning_vi, example, count`).
Import it:

```bash
python -m scripts.import_vocab "..\AI_Reader_Document\output\_vocab.csv" \
  --source "ETS 2026 Test 1" --lang en --level B1

# or every CSV in a folder
python -m scripts.import_vocab "*.csv"
```

Or upload through the API:

```bash
curl -F "file=@_vocab.csv" -F "source_name=ETS 2026" -F "language=en" \
  http://localhost:8000/import
```

Language is auto-detected (a `traditional` column ⇒ `zh`), and can be overridden.
Re-importing the same `source_name` **replaces** the previous import.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/words` | List/search words (see filters below) |
| GET | `/words/{id}` | One word |
| GET | `/sources` | Imported documents |
| DELETE | `/sources/{id}` | Delete a document and its words |
| GET | `/stats` | Counts by language/level |
| POST | `/import` | Upload a CSV |

`GET /words` query params: `lang` (`en`/`zh`), `level` (`B1`, `HSK3`…),
`q` (search), `source_id`, `order` (`level`|`word`|`recent`), `limit`, `offset`.

```bash
curl "http://localhost:8000/words?lang=zh&level=HSK3&q=提高&limit=20&offset=0"
```

Response:

```json
{
  "total": 66,
  "limit": 20,
  "offset": 0,
  "items": [
    {"id": 1, "word": "提高", "traditional": "提高", "language": "zh",
     "level": "HSK3", "pos": "v", "ipa": "tí gāo",
     "definition_en": "to raise", "meaning_vi": "nâng cao",
     "example": "我们要提高生产力", "source_id": 2,
     "created_at": "2026-10-12T00:00:00Z"}
  ]
}
```

## Android (Retrofit + Moshi/Gson)

```kotlin
data class Word(
    val id: Int, val word: String, val traditional: String?,
    val language: String, val level: String, val pos: String?,
    val ipa: String?, val definition_en: String?, val meaning_vi: String?,
    val example: String?, val source_id: Int?,
)

data class WordPage(
    val total: Int, val limit: Int, val offset: Int, val items: List<Word>,
)

interface Api {
    @GET("words")
    suspend fun getWords(
        @Query("lang") lang: String? = null,
        @Query("level") level: String? = null,
        @Query("q") q: String? = null,
        @Query("limit") limit: Int = 20,
        @Query("offset") offset: Int = 0,
    ): WordPage
}
```

Base URL: `http://10.0.2.2:8000/` (emulator → host machine) or your server/LAN IP.
For release builds, use HTTPS and remove `usesCleartextTraffic`.

## Switch to PostgreSQL

```bash
set DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/aireader
```
(install `psycopg[binary]`). Tables are created automatically on startup.

## Tests

```bash
pip install -r requirements-dev.txt
python tests/test_api.py
```
