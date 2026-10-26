# AI Reader Backend ? API Reference

Base URL: `http://localhost:8000`  
Production: `https://aireaderbackend-production.up.railway.app`  
Interactive docs: `/docs`

---

## Authentication

N?u `API_KEYS` r?ng ? auth **t?t** (dev).  
N?u có key ? m?i endpoint tr? `GET /` và `GET /health` c?n:

```http
X-API-Key: <key>
Authorization: Bearer <key>
```

---

## Models

### `WordOut`

| Field | Type |
|---|---|
| `id` | `int` |
| `word` | `string` |
| `traditional` | `string` |
| `language` | `string` |
| `level` | `string` |
| `pos` / `ipa` / `definition_en` / `meaning_vi` / `example` | `string` |
| `source_id` | `int \| null` |
| `created_at` | `datetime` |

### `WordPage`

`total`, `limit`, `offset`, `items: WordOut[]`

### `SourceOut`

`id`, `name`, `language`, `level`, `count`, `imported_at`

### `ProgressOut`

| Field | Type |
|---|---|
| `user_id` | `string` |
| `current_source_id` | `int \| null` |
| `current_source_name` | `string` |
| `current_source_language` | `string` |
| `current_source_level` | `string` |
| `current_source_count` | `int` |
| `streak_count` | `int` |
| `last_study_date` | `string` (`YYYY-MM-DD`) |
| `updated_at` | `datetime` |

---

## Endpoints

| Method | Path | Mô t? |
|---|---|---|
| `GET` | `/` | Meta (public) |
| `GET` | `/health` | Health (public) |
| `GET` | `/words` | List / filter t? |
| `POST` | `/words/search` | Search (JSON body) |
| `GET` | `/words/{id}` | Chi ti?t 1 t? |
| `GET` | `/stats` | Th?ng kê |
| `GET` | `/export` | Download JSON |
| `GET` | `/sources` | Danh sách bài |
| `DELETE` | `/sources/{id}` | Xóa bài + t? |
| `PUT` | `/progress/{user_id}` | L?u bài ?ang h?c / streak |
| `POST` | `/progress/{user_id}/check-in` | Check-in hôm nay + t?ng streak |
| `GET` | `/progress/{user_id}` | ??c ti?n ?? |
| `POST` | `/import` | Upload CSV |

---

## Progress (Android)

App ?ang g?i ?úng các path sau:

### `PUT /progress/{user_id}`

Body (m?i field optional):

```json
{
  "current_source_id": 1,
  "current_source_name": "HSK1",
  "current_source_language": "zh",
  "current_source_level": "HSK1+",
  "current_source_count": 114,
  "streak_count": 3,
  "last_study_date": "2026-10-20"
}
```

### `POST /progress/{user_id}/check-in`

```json
{
  "source_id": 1,
  "source_name": "HSK1",
  "source_language": "zh",
  "source_level": "HSK1+",
  "source_count": 114,
  "study_date": "2026-10-20"
}
```

Streak: cùng ngày không t?ng; ngày li?n +1; ng?t / l?n ??u = 1.

### `GET /progress/{user_id}`

`404` n?u ch?a t?ng l?u.

```bash
curl -X POST https://aireaderbackend-production.up.railway.app/progress/USER_ID/check-in \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d "{\"source_id\":1,\"study_date\":\"2026-10-20\"}"
```

---

## Learning words (Chieng flashcards)

| Method | Path |
|---|---|
| `GET` | `/learning-words/{user_id}` |
| `PUT` | `/learning-words/{user_id}` |
| `PUT` | `/learning-words/{user_id}/{word_id}` |
| `DELETE` | `/learning-words/{user_id}/{word_id}` |

Batch upsert body:

```json
{
  "items": [
    {
      "word_id": 12,
      "word": "??",
      "status": "LEARNING",
      "meaning_vi": "xin chào",
      "updated_at_epoch_ms": 1730000000000
    }
  ]
}
```

`status`: `LEARNING` | `KNOWN` | `REVIEW`. Conflict: keep row with newer `updated_at_epoch_ms`.

---

## Chat logs (Chieng AI tutor history)

App g?i DeepSeek tr?c ti?p; Railway ch? l?u transcript khi user ?ã ??ng nh?p.

| Method | Path |
|---|---|
| `POST` | `/chat-logs/{user_id}/sessions` |
| `POST` | `/chat-logs/{user_id}/messages` |
| `GET` | `/chat-logs/{user_id}/sessions` |
| `GET` | `/chat-logs/{user_id}/sessions/{session_id}/messages` |

Create session:

```json
{ "locale": "vi" }
```

Append message (`role`: `user` \| `assistant`):

```json
{
  "session_id": "uuid",
  "role": "user",
  "content": "??",
  "client_message_id": "local-uuid",
  "model": "deepseek-chat",
  "locale": "vi",
  "created_at_epoch_ms": 1730000000000
}
```

Cùng `user_id` + `client_message_id` ? idempotent (tr? b?n ghi c?).

## Import CSV

Khuy?n ngh? (xlsx/csv, key t? env — xem `docs/IMPORT.md`):

```powershell
$env:AIREADER_API_KEY="..."   # from Railway API_KEYS — never commit
python -m scripts.upload_railway "path\to\file.xlsx" --lang zh --level HSK2+
```

Ho?c curl (CSV; PowerShell dùng `curl.exe`):

```bash
curl.exe -F "file=@vocab.csv" -F "language=zh" -F "level=HSK1+" \
  -H "X-API-Key: $env:AIREADER_API_KEY" \
  https://aireaderbackend-production.up.railway.app/import
```

