@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo Starting AI Reader API at http://localhost:8000  (docs: /docs)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
