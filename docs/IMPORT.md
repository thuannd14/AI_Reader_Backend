# Hướng dẫn import vocabulary vào Backend

Package này giải thích: **data nằm đâu**, và **lần sau import file tương tự thế nào**.

---

## 1. Data được lưu ở đâu?

Mặc định dùng **SQLite**, file nằm tại:

```text
ai-reader-backend/
└── data/
    └── app.db          ← toàn bộ vocabulary + sources
```

| Thành phần | Vị trí | Ghi chú |
|---|---|---|
| Database | `data/app.db` | Bảng `source` + `vocabulary` |
| Config | `DATABASE_URL` (env) | Để trống = SQLite ở trên |
| Postgres (tuỳ chọn) | server Postgres | Đặt `DATABASE_URL=postgresql+psycopg://...` |

**Lưu ý**

- `data/app.db` **không** commit lên git (đã có trong `.gitignore`).
- Xóa `data/app.db` = mất toàn bộ data local (có thể import lại từ CSV/XLSX).
- Docker: file DB gắn volume `./data` → vẫn là `./data/app.db` trên máy host.

### Schema trong DB

```text
Source          → 1 tài liệu đã import (tên, lang, level, số từ)
Vocabulary      → từng từ, gắn source_id
```

Import lại **cùng `source_name`** → xóa source cũ + từ cũ, rồi ghi mới (idempotent).

---

## 2. File đầu vào cần dạng gì?

Backend nhận **CSV** hoặc **XLSX** (sheet đầu), với các cột chuẩn:

| Cột | Bắt buộc? | Mô tả |
|---|---|---|
| `word` | có | Từ / cụm từ |
| `traditional` | không | Có cột này → auto language = `zh` |
| `level` | không | `HSK1`, `B1`… |
| `pos` | không | Loại từ |
| `ipa` | không | IPA / pinyin |
| `definition_en` | không | Nghĩa EN |
| `meaning_vi` | không | Nghĩa VI |
| `example` | không | Ví dụ |
| `count` | không | (bỏ qua khi lưu DB) |

Cột thừa (`memo`, `etymology`…) được **bỏ qua**, không làm lỗi import.

Nguồn file thường từ tool `AI_Reader_Document`:

```text
AI_Reader_Document/output/
  ├── xxx_TuVung_HSK1+_p010-017.xlsx
  ├── xxx_TuVung_HSK1+_p010-017.docx
  └── …_vocab.csv   (nếu tool xuất CSV)
```

---

## 3. Lần sau import file tương tự — 3 bước

### Bước A — Cài dependency (một lần)

```bash
cd D:\Android_Project_Personal\ai-reader-backend
pip install -r requirements.txt
pip install openpyxl          # cần nếu import .xlsx
```

### Bước B — Chạy lệnh import

**Một file Excel (khuyến nghị):**

```bash
python -m scripts.import_vocab ^
  "D:\Android_Project_Personal\AI_Reader_Document\output\新HSK1教程3.0_TuVung_HSK1+_p010-017.xlsx" ^
  --lang zh --level HSK1+
```

**Một file CSV:**

```bash
python -m scripts.import_vocab "path\to\_vocab.csv" --source "Ten Tai Lieu" --lang zh --level HSK1
```

**Nhiều file / cả folder:**

```bash
python -m scripts.import_vocab "D:\...\AI_Reader_Document\output\*.xlsx"
python -m scripts.import_vocab "D:\...\output\*.csv" "D:\...\output\*.xlsx"
```

**Tham số CLI**

| Flag | Ý nghĩa | Mặc định |
|---|---|---|
| `--source` | Tên source trong DB | Tên file (CSV) / stem (XLSX) |
| `--lang` | `en` hoặc `zh` | Auto (có cột `traditional` → `zh`) |
| `--level` | Level ghi trên Source | Lấy từ CSV nếu đồng nhất |

Output mẫu:

```text
Imported  114 words [zh/HSK1+] <- xxx.xlsx  (skipped 0, source_id=2)
Done. 114 words inserted.
```

### Bước C — Kiểm tra

```bash
# chạy server (nếu chưa chạy)
run.bat

# hoặc test nhanh không cần server
python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); print(c.get('/stats').json()); print(c.get('/sources').json())"
```

API app sẽ đọc:

| Endpoint | Mục đích |
|---|---|
| `GET /sources` | Xem tài liệu vừa import |
| `GET /words?lang=zh&source_id=2` | Lấy từ theo source |
| `GET /stats` | Tổng số từ / level |

---

## 4. Upload lên Railway (production) — khuyến nghị

CLI `import_vocab` **không** đẩy lên Railway trừ khi bạn set `DATABASE_URL`
production. Muốn app online thấy từ mới → upload qua API.

**Production URL:** `https://aireaderbackend-production.up.railway.app`

### Bảo mật API key

- Key nằm trên Railway Variables (`API_KEYS`) — **không** commit vào git / docs.
- Trên máy local, set env mỗi session (hoặc User env Windows):

```powershell
$env:AIREADER_API_KEY="paste_key_from_railway_here"
```

### Cách nhanh (xlsx hoặc csv)

```powershell
cd D:\Android_Project_Personal\ai-reader-backend

# lần đầu mỗi cửa sổ PowerShell:
$env:AIREADER_API_KEY="..."
```

**Tiếng Trung (HSK):**

```powershell
python -m scripts.upload_railway `
  "D:\Android_Project_Personal\AI_Reader_Document\output\FILE.xlsx" `
  --lang zh --level HSK2+
```

**Tiếng Anh (CEFR):**

```powershell
python -m scripts.upload_railway `
  "D:\Android_Project_Personal\AI_Reader_Document\output\ETS 2026- RC_TuVung_B2_p140-167.csv" `
  --lang en --level B2
```

Script tự đổi `.xlsx` → CSV rồi `POST /import`. Output mẫu:

```text
Uploaded 54 words [zh/HSK2+] <- ...  (skipped 0, source_id=2)
Uploaded 104 words [en/B2] <- ETS 2026- RC_TuVung_B2_p140-167  (skipped 0, source_id=4)
```

> Không có cột `traditional` → auto `en`; có cột `traditional` → auto `zh`. Vẫn nên truyền `--lang` / `--level` rõ ràng.

### Curl thủ công (chỉ CSV; dùng `curl.exe` trên PowerShell)

```powershell
# zh
curl.exe -F "file=@D:\path\to\file.csv" `
  -F "source_name=Ten_Source" `
  -F "language=zh" `
  -F "level=HSK2+" `
  -H "X-API-Key: $env:AIREADER_API_KEY" `
  https://aireaderbackend-production.up.railway.app/import

# en
curl.exe -F "file=@D:\path\to\english.csv" `
  -F "source_name=ETS_B2" `
  -F "language=en" `
  -F "level=B2" `
  -H "X-API-Key: $env:AIREADER_API_KEY" `
  https://aireaderbackend-production.up.railway.app/import
```

### Local only (SQLite `data/app.db`)

```bash
python -m scripts.import_vocab "path\to\file.xlsx" --lang zh --level HSK1+
```

Hoặc `POST http://localhost:8000/import` khi `run.bat` đang chạy.

---

## 5. Checklist lần sau (copy nhanh)

```text
[ ] 1. Tool AI_Reader_Document đã xuất .xlsx/.csv trong output/
[ ] 2. cd ai-reader-backend
[ ] 3. $env:AIREADER_API_KEY="..."   (nếu chưa set trong session)
[ ] 4. python -m scripts.upload_railway "PATH\file.xlsx" --lang zh --level HSK2+
       hoặc: python -m scripts.upload_railway "PATH\file.csv" --lang en --level B2
[ ] 5. Kiểm tra: GET /sources hoặc /stats trên domain Railway
```

---

## 6. Xử lý sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `openpyxl is required` | `pip install openpyxl` |
| `Unsupported file type` | Chỉ `.csv` / `.xlsx` / `.xlsm` |
| Import 0 từ | Thiếu cột `word`, hoặc file rỗng |
| App không thấy data | Sai base URL / chưa restart server / filter `lang`/`source_id` sai |
| Import local nhưng app Railway không có | Phải dùng `upload_railway` (mục 4), không dùng `import_vocab` |
| `401` khi upload Railway | Sai / thiếu `$env:AIREADER_API_KEY` |
| PowerShell `curl` lỗi | Dùng `curl.exe` hoặc script `upload_railway` |
| Muốn xóa 1 tài liệu | `DELETE /sources/{id}` hoặc import lại cùng `--source` |
| Muốn reset hết DB local | Xóa `data/app.db`, chạy lại import |

---

## 7. Sơ đồ luồng

```text
AI_Reader_Document  →  .xlsx / .csv
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
  upload_railway (production)     import_vocab (local)
           │                               │
           ▼                               ▼
   Railway Postgres                  data/app.db
           │
           ▼
   Android app (HTTPS)
```
