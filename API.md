# AI Reader Backend — API Reference

Base URL: `http://localhost:8000`  
Android emulator → host: `http://10.0.2.2:8000`  
Interactive docs: <http://localhost:8000/docs>

---

## Authentication

Nếu `API_KEYS` rỗng → auth **tắt** (dev).  
Nếu có key → mọi endpoint trừ `GET /` và `GET /health` cần một trong hai header:

```http
X-API-Key: <key>
Authorization: Bearer <key>
```

Sai / thiếu key → `401 Unauthorized` với body:

```json
{ "detail": "Invalid or missing API key" }
```

---

## Models dùng chung

### `WordOut`

| Field | Type | Mô tả |
|---|---|---|
| `id` | `int` | ID từ |
| `word` | `string` | Từ / cụm từ |
| `traditional` | `string` | Chữ phồn thể (zh), mặc định `""` |
| `language` | `string` | `"en"` \| `"zh"` |
| `level` | `string` | CEFR (`B1`…) hoặc HSK (`HSK3`…) |
| `pos` | `string` | Part of speech |
| `ipa` | `string` | IPA hoặc pinyin |
| `definition_en` | `string` | Định nghĩa tiếng Anh |
| `meaning_vi` | `string` | Nghĩa tiếng Việt |
| `example` | `string` | Ví dụ |
| `source_id` | `int \| null` | ID tài liệu nguồn |
| `created_at` | `datetime` | ISO 8601 |

### `WordPage`

| Field | Type |
|---|---|
| `total` | `int` |
| `limit` | `int` |
| `offset` | `int` |
| `items` | `WordOut[]` |

### `SourceOut`

| Field | Type |
|---|---|
| `id` | `int` |
| `name` | `string` |
| `language` | `string` |
| `level` | `string` |
| `count` | `int` |
| `imported_at` | `datetime` |

### `ImportResult`

| Field | Type |
|---|---|
| `source_id` | `int` |
| `source` | `string` |
| `language` | `string` |
| `level` | `string` |
| `imported` | `int` |
| `skipped` | `int` |

### `Stats`

| Field | Type |
|---|---|
| `total_words` | `int` |
| `total_sources` | `int` |
| `languages` | `object` — map `lang → count`, ví dụ `{ "en": 80, "zh": 20 }` |
| `levels` | `object` — map `level → count`, ví dụ `{ "B1": 40, "HSK3": 20 }` |

### `WordQuery` (body của `POST /words/search`)

| Field | Type | Default |
|---|---|---|
| `lang` | `string \| null` | `null` |
| `level` | `string \| null` | `null` |
| `q` | `string \| null` | `null` |
| `source_id` | `int \| null` | `null` |
| `order` | `string` | `"level"` |
| `limit` | `int` | `20` |
| `offset` | `int` | `0` |

---

## Endpoints

### 1. `GET /` — Meta *(public)*

**Auth:** không cần  

**Input:** không  

**Output:**

```json
{
  "name": "AI Reader Vocabulary API",
  "version": "...",
  "docs": "/docs"
}
```

---

### 2. `GET /health` — Health check *(public)*

**Auth:** không cần  

**Input:** không  

**Output:**

```json
{ "status": "ok" }
```

---

### 3. `GET /words` — Danh sách / tìm từ

**Auth:** cần (nếu `API_KEYS` bật)

**Query parameters**

| Param | Type | Default | Ràng buộc / mô tả |
|---|---|---|---|
| `lang` | `string?` | `null` | `"en"` / `"zh"` (case-insensitive) |
| `level` | `string?` | `null` | `"B1"`, `"HSK3"`… (case-insensitive) |
| `q` | `string?` | `null` | Search trong `word` / `meaning_vi` / `definition_en` |
| `source_id` | `int?` | `null` | Lọc theo source |
| `order` | `string` | `"level"` | `"level"` \| `"word"` \| `"recent"` |
| `limit` | `int` | `20` | `1`–`200` |
| `offset` | `int` | `0` | `≥ 0` |

**Output:** `WordPage`

```json
{
  "total": 66,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "word": "提高",
      "traditional": "提高",
      "language": "zh",
      "level": "HSK3",
      "pos": "v",
      "ipa": "tí gāo",
      "definition_en": "to raise",
      "meaning_vi": "nâng cao",
      "example": "我们要提高生产力",
      "source_id": 2,
      "created_at": "2026-10-12T00:00:00Z"
    }
  ]
}
```

**Ví dụ:**

```bash
curl "http://localhost:8000/words?lang=en&level=B1&limit=20&offset=0"
```

---

### 4. `POST /words/search` — Tìm từ (JSON body)

Giống `GET /words`, nhưng tham số nằm trong body JSON thay vì query string.

**Auth:** cần (nếu `API_KEYS` bật)

**Input (JSON body):** `WordQuery`

```json
{
  "lang": "en",
  "level": "B1",
  "q": null,
  "source_id": null,
  "order": "level",
  "limit": 20,
  "offset": 0
}
```

- `order` không hợp lệ → fallback `"level"`
- `limit` bị clamp về `1`–`200`
- `offset` bị clamp về `≥ 0`

**Output:** `WordPage`

**Ví dụ:**

```bash
curl -X POST http://localhost:8000/words/search \
  -H "Content-Type: application/json" \
  -d '{"lang":"en","level":"B1","limit":20,"offset":0}'
```

---

### 5. `GET /words/{word_id}` — Chi tiết một từ

**Auth:** cần (nếu `API_KEYS` bật)

**Path parameters**

| Param | Type | Mô tả |
|---|---|---|
| `word_id` | `int` | ID từ |

**Output:** `WordOut`

**Errors**

| Status | Body |
|---|---|
| `404` | `{ "detail": "Word not found" }` |

---

### 6. `GET /stats` — Thống kê

**Auth:** cần (nếu `API_KEYS` bật)

**Input:** không  

**Output:** `Stats`

```json
{
  "total_words": 100,
  "total_sources": 3,
  "languages": { "en": 80, "zh": 20 },
  "levels": { "B1": 40, "HSK3": 20 }
}
```

---

### 7. `GET /export` — Tải vocabulary dạng JSON file

**Auth:** cần (nếu `API_KEYS` bật)

**Query parameters**

| Param | Type | Default | Mô tả |
|---|---|---|---|
| `lang` | `string?` | `null` | Lọc ngôn ngữ |
| `level` | `string?` | `null` | Lọc level |

**Output:** JSON file download

Header: `Content-Disposition: attachment; filename="vocabulary.json"`

```json
{
  "count": 10,
  "lang": "en",
  "level": "B1",
  "items": [ /* WordOut[] */ ]
}
```

**Ví dụ:**

```bash
curl -o vocabulary.json http://localhost:8000/export
curl -o zh.json "http://localhost:8000/export?lang=zh&level=HSK3"
```

---

### 8. `GET /sources` — Danh sách tài liệu đã import

**Auth:** cần (nếu `API_KEYS` bật)

**Input:** không  

**Output:** `SourceOut[]` (sắp xếp `imported_at` giảm dần)

```json
[
  {
    "id": 1,
    "name": "ETS 2026 Test 1",
    "language": "en",
    "level": "B1",
    "count": 120,
    "imported_at": "2026-10-12T00:00:00Z"
  }
]
```

---

### 9. `DELETE /sources/{source_id}` — Xóa source và toàn bộ từ liên quan

**Auth:** cần (nếu `API_KEYS` bật)

**Path parameters**

| Param | Type | Mô tả |
|---|---|---|
| `source_id` | `int` | ID source |

**Output:**

```json
{ "deleted": 1 }
```

**Errors**

| Status | Body |
|---|---|
| `404` | `{ "detail": "Source not found" }` |

---

### 10. `POST /import` — Upload CSV vocabulary

**Auth:** cần (nếu `API_KEYS` bật)

**Content-Type:** `multipart/form-data`

**Form fields**

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `file` | file | có | CSV từ AI_Reader_Document tool |
| `language` | `string?` | không | `"en"` / `"zh"` (override; auto-detect nếu có cột `traditional`) |
| `level` | `string?` | không | Override level |
| `source_name` | `string?` | không | Tên source; mặc định = tên file |

**Output:** `ImportResult`

```json
{
  "source_id": 1,
  "source": "ETS 2026",
  "language": "en",
  "level": "B1",
  "imported": 120,
  "skipped": 3
}
```

**Notes**

- Re-import cùng `source_name` sẽ **thay thế** import cũ.
- CSV schema: `word, [traditional], level, pos, ipa, definition_en, meaning_vi, example, count`

**Errors**

| Status | Body |
|---|---|
| `400` | `{ "detail": "<lỗi parse/import>" }` |

**Ví dụ:**

```bash
curl -F "file=@_vocab.csv" -F "source_name=ETS 2026" -F "language=en" \
  http://localhost:8000/import
```

---

## Gợi ý endpoint cho Android app

| Endpoint | Mục đích thường dùng trong app |
|---|---|
| `GET /health` | Kiểm tra server sống |
| `GET /words` hoặc `POST /words/search` | List / filter / search từ vựng |
| `GET /words/{id}` | Màn chi tiết một từ |
| `GET /sources` | Danh sách tài liệu |
| `GET /stats` | Thống kê |
| `GET /export` | Đồng bộ / backup (tuỳ app) |
| `POST /import` | Thường dùng tool/admin, ít dùng trong app đọc |
| `DELETE /sources/{id}` | Thường dùng tool/admin |

---

## Android (OkHttp) — gửi API key

```kotlin
val client = OkHttpClient.Builder()
    .addInterceptor { chain ->
        val req = chain.request().newBuilder()
            .addHeader("X-API-Key", BuildConfig.API_KEY)
            .build()
        chain.proceed(req)
    }
    .build()
```
