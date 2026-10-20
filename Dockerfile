# AI Reader Vocabulary API — production image (Railway / Docker)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (better layer caching)
COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt

# Application code
COPY app ./app
COPY scripts ./scripts

# SQLite fallback directory (Railway uses Postgres via DATABASE_URL)
RUN mkdir -p /app/data

EXPOSE 8000

# Railway sets PORT; local default 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
