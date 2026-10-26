# AI Reader Vocabulary API — production image (Railway / Docker)
# Includes optional OpenPronounce (English pronunciation) — large image (~GB models on first use).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENABLE_OPENPRONOUNCE=1 \
    OPENPRONOUNCE_DEVICE=cpu \
    OPENPRONOUNCE_TTS=gtts \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-postgres.txt requirements-pronunciation.txt ./

RUN pip install --no-cache-dir -r requirements.txt -r requirements-postgres.txt \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-pronunciation.txt

COPY app ./app
COPY scripts ./scripts

RUN mkdir -p /app/data /app/.cache/huggingface

EXPOSE 8000

# Railway sets PORT; local default 8000
# First /pronunciation/assess may download Wav2Vec2 weights (~GB) — needs enough RAM/disk.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
