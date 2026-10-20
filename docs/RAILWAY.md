# Deploy lên Railway

Hướng dẫn host API **không cần bật máy** — dùng Docker + PostgreSQL trên Railway.

---

## 0. Chuẩn bị

- Tài khoản [Railway](https://railway.app)
- Repo GitHub: `https://github.com/thuannd14/AI_Reader_Backend.git` (đã có remote)
- Commit & push code mới nhất (Dockerfile + `railway.toml`) lên `master`

---

## 1. Tạo project trên Railway

1. Vào [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub repo** → chọn `AI_Reader_Backend`
3. Railway sẽ build bằng `Dockerfile` (đã cấu hình trong `railway.toml`)

---

## 2. Thêm PostgreSQL

1. Trong project → **+ New** → **Database** → **PostgreSQL**
2. Railway tự tạo biến `DATABASE_URL` trên service Postgres
3. Vào service **API** → **Variables** → **Add Reference** / **Variable**  
   - Thêm `DATABASE_URL` trỏ tới Postgres  
   - Hoặc dùng **Connect** / shared variables giữa Postgres và API

App tự đổi `postgres://…` → `postgresql+psycopg://…` (xem `app/config.py`).

---

## 3. Biến môi trường (API service)

| Variable | Bắt buộc | Ví dụ / ghi chú |
|---|---|---|
| `DATABASE_URL` | có | Reference từ Postgres plugin |
| `API_KEYS` | khuyến nghị | Key bí mật cho app Android |
| `PORT` | không | Railway tự set |

Tạo key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Ví dụ:

```text
API_KEYS=your_generated_key_here
```

> Production: **luôn bật** `API_KEYS`. Để trống = API public.

---

## 4. Public domain

1. Service API → **Settings** → **Networking** → **Generate Domain**
2. URL dạng: `https://ai-reader-backend-production-xxxx.up.railway.app`
3. Kiểm tra:

```bash
curl https://YOUR-DOMAIN/health
# {"status":"ok"}
```

Docs: `https://YOUR-DOMAIN/docs`

---

## 5. Import vocabulary lên production

Từ máy local (file CSV):

```bash
curl -F "file=@data/新HSK1教程3.0_TuVung_HSK1+_p010-017.csv" ^
  -F "source_name=新HSK1教程3.0_TuVung_HSK1+_p010-017" ^
  -F "language=zh" ^
  -F "level=HSK1+" ^
  -H "X-API-Key: YOUR_KEY" ^
  https://YOUR-DOMAIN/import
```

Hoặc dùng CLI với `DATABASE_URL` production (ít dùng hơn):

```bash
set DATABASE_URL=postgresql+psycopg://...
python -m scripts.import_vocab "path\to\file.xlsx" --lang zh --level HSK1+
```

---

## 6. Android

Đổi base URL Retrofit sang:

```text
https://YOUR-DOMAIN/
```

Gửi header:

```text
X-API-Key: YOUR_KEY
```

---

## 7. Checklist

```text
[ ] Push code lên GitHub
[ ] New Project → Deploy from GitHub
[ ] Add PostgreSQL + gắn DATABASE_URL vào API
[ ] Set API_KEYS
[ ] Generate Domain
[ ] curl /health → ok
[ ] POST /import CSV
[ ] GET /words?lang=zh → có data
[ ] Đổi base URL app Android
```

---

## 8. Lưu ý chi phí / free tier

- Railway có trial credit / plan trả phí theo usage — xem bảng giá hiện tại trên site.
- SQLite **không** dùng trên Railway (filesystem ephemeral) → bắt buộc Postgres như trên.
- Mỗi lần git push `master` → Railway tự rebuild & redeploy (nếu đã bật auto-deploy).

---

## 9. Troubleshooting

| Lỗi | Cách xử lý |
|---|---|
| Build fail thiếu `psycopg` | Image đã cài `requirements-postgres.txt` — pull lại code mới |
| `connection refused` DB | Chưa reference `DATABASE_URL` vào API service |
| `401` khi gọi API | Sai / thiếu `X-API-Key` |
| `/import` 400 | File không phải CSV đúng schema |
| App không gọi được | Dùng HTTPS domain Railway, không dùng `localhost` |
