"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class WordOut(BaseModel):
    id: int
    word: str
    traditional: str = ""
    language: str
    level: str
    pos: str = ""
    ipa: str = ""
    definition_en: str = ""
    meaning_vi: str = ""
    example: str = ""
    source_id: int | None = None
    created_at: datetime


class WordPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[WordOut]


class SourceOut(BaseModel):
    id: int
    name: str
    language: str
    level: str
    count: int
    imported_at: datetime


class ImportResult(BaseModel):
    source_id: int
    source: str
    language: str
    level: str
    imported: int
    skipped: int


class Stats(BaseModel):
    total_words: int
    total_sources: int
    languages: dict[str, int]
    levels: dict[str, int]


class WordQuery(BaseModel):
    """Request body for POST /words/search (alternative to GET query params)."""

    lang: str | None = None
    level: str | None = None
    q: str | None = None
    source_id: int | None = None
    order: str = "level"
    limit: int = 20
    offset: int = 0


class ProgressUpdate(BaseModel):
    """Upsert learning progress for one device / install."""

    device_id: str = Field(..., min_length=1, max_length=128)
    source_id: int | None = None
    word_id: int | None = None
    # When true, bump streak using study_date (or server UTC today).
    record_study: bool = True
    # Client local calendar date YYYY-MM-DD (recommended for correct streak).
    study_date: date | None = None


class ProgressOut(BaseModel):
    device_id: str
    source_id: int | None = None
    word_id: int | None = None
    streak_days: int
    last_study_date: date | None = None
    updated_at: datetime
