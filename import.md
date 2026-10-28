# Import vocabulary lên Railway (copy nhanh)

**Bảo mật:** Không commit API key / domain thật vào git.

Set tạm trong PowerShell (lấy từ Railway Variables / Settings):

```powershell
$env:AIREADER_API_KEY="<API_KEY>"
$env:AIREADER_API_BASE="https://<YOUR_DOMAIN>"
```

---

## Upload (xlsx hoặc csv)

```powershell
cd D:\Android_Project_Personal\ai-reader-backend

$env:AIREADER_API_KEY="<API_KEY>"
$env:AIREADER_API_BASE="https://<YOUR_DOMAIN>"
```

### Tiếng Trung (HSK)

```powershell
python -m scripts.upload_railway `
  "D:\Android_Project_Personal\AI_Reader_Document\output\FILE.xlsx" `
  --lang zh --level HSK2+ `
  --base $env:AIREADER_API_BASE
```

### Tiếng Anh (CEFR)

```powershell
python -m scripts.upload_railway `
  "D:\Android_Project_Personal\AI_Reader_Document\output\ETS 2026- RC_TuVung_B2_p140-167.csv" `
  --lang en --level B2 `
  --base $env:AIREADER_API_BASE
```

Đổi path file, `--lang` (`zh` / `en`), `--level` (`HSK2+` / `B1` / `B2`…) cho đúng bài.

Output mẫu:

```text
Uploaded 54 words [zh/HSK2+] <- ...  (skipped 0, source_id=3)
Uploaded 104 words [en/B2] <- ETS 2026- RC_TuVung_B2_p140-167  (skipped 0, source_id=4)
```

---

## Kiểm tra

```powershell
curl.exe -H "X-API-Key: $env:AIREADER_API_KEY" `
  "$env:AIREADER_API_BASE/sources"

curl.exe -H "X-API-Key: $env:AIREADER_API_KEY" `
  "$env:AIREADER_API_BASE/stats"
```

---

## Lưu ý

| Việc | Lệnh |
|---|---|
| Lên **Railway** (app online) | `python -m scripts.upload_railway ...` |
| Chỉ **local** (`data/app.db`) | `python -m scripts.import_vocab ...` |

Chi tiết đầy đủ: [`docs/IMPORT.md`](docs/IMPORT.md), [`docs/RAILWAY.md`](docs/RAILWAY.md).
