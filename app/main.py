"""FastAPI application entrypoint.

Run (dev):
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .config import API_TITLE, API_VERSION
from .auth import require_api_key
from .db import get_session, init_db
from .importer import import_csv_stream
from .routers import chat, chat_logs, learning_words, progress, sources, words
from .schemas import ImportResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)

# Allow the Android app / browser tools to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": API_TITLE, "version": API_VERSION, "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/learning-words-schema", tags=["meta"], dependencies=[Depends(require_api_key)])
def learning_words_schema() -> dict:
    """Debug: report Postgres udt_name for learningword epoch columns."""
    from sqlalchemy import text

    from .db import engine
    from .config import DATABASE_URL

    if "postgres" not in DATABASE_URL:
        return {"db": "non-postgres", "columns": {}}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT table_name, column_name, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND (
                    table_name IN ('learningword', 'learning_word', 'learning_words')
                    OR column_name IN ('added_at_epoch_ms', 'updated_at_epoch_ms')
                  )
                ORDER BY table_name, column_name
                """
            )
        ).fetchall()
    return {
        "columns": [
            {"table": r[0], "column": r[1], "udt": r[2]} for r in rows
        ]
    }


@app.post("/import", response_model=ImportResult, tags=["import"],
          dependencies=[Depends(require_api_key)])
async def upload_csv(
    file: UploadFile = File(..., description="vocabulary CSV from the tool"),
    language: str | None = Form(None, description='optional "en" or "zh"'),
    level: str | None = Form(None, description="optional level override"),
    source_name: str | None = Form(None),
    session: Session = Depends(get_session),
) -> ImportResult:
    data = await file.read()
    name = source_name or file.filename or "upload.csv"
    try:
        result = import_csv_stream(
            session, data, name, language=language or None, level=level or None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportResult(**result)


app.include_router(words.router)
app.include_router(sources.router)
app.include_router(progress.router)
app.include_router(learning_words.router)
app.include_router(chat.router)
app.include_router(chat_logs.router)
