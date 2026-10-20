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

## 4. Cách khác: upload qua API

Khi server đang chạy:

```bash
curl -F "file=@vocab.xlsx" ^
  -F "source_name=Bai 1" ^
  -F "language=zh" ^
  -F "level=HSK1+" ^
  http://localhost:8000/import
```

> Endpoint `/import` hiện nhận **CSV upload**. Với `.xlsx`, dùng CLI ở mục 3 (khuyến nghị).

Nếu bật `API_KEYS`, thêm: `-H "X-API-Key: your_key"`.

---

## 5. Checklist lần sau (copy nhanh)

```text
[ ] 1. Tool AI_Reader_Document đã xuất .xlsx hoặc .csv trong output/
[ ] 2. cd ai-reader-backend
[ ] 3. python -m scripts.import_vocab "PATH\file.xlsx" --lang zh --level HSK1+
[ ] 4. Xem source_id trong log / GET /sources
[ ] 5. App gọi GET /words?source_id=<id>  → data hiện lên
```

---

## 6. Xử lý sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `openpyxl is required` | `pip install openpyxl` |
| `Unsupported file type` | Chỉ `.csv` / `.xlsx` / `.xlsm` |
| Import 0 từ | Thiếu cột `word`, hoặc file rỗng |
| App không thấy data | Sai base URL / chưa restart server / filter `lang`/`source_id` sai |
| Muốn xóa 1 tài liệu | `DELETE /sources/{id}` hoặc import lại cùng `--source` |
| Muốn reset hết DB local | Xóa `data/app.db`, chạy lại import |

---

## 7. Sơ đồ luồng

```text
AI_Reader_Document  →  .xlsx / .csv
                           │
                           ▼
            python -m scripts.import_vocab ...
                           │
                           ▼
                     data/app.db
                           │
              FastAPI  GET /words, /sources
                           │
                           ▼
                      Android app
```
