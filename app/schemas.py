"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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


class ProgressOut(BaseModel):
    user_id: str
    current_source_id: int | None = None
    current_source_name: str = ""
    current_source_language: str = ""
    current_source_level: str = ""
    current_source_count: int = 0
    streak_count: int = 0
    last_study_date: str = ""
    updated_at: datetime


class ProgressUpsert(BaseModel):
    """Body for PUT /progress/{user_id} — save continue pointer / streak."""

    current_source_id: int | None = None
    current_source_name: str = ""
    current_source_language: str = ""
    current_source_level: str = ""
    current_source_count: int = 0
    streak_count: int | None = None
    last_study_date: str = ""


class StudyCheckIn(BaseModel):
    """Body for POST /progress/{user_id}/check-in — open a lesson + bump streak."""

    source_id: int
    source_name: str = ""
    source_language: str = ""
    source_level: str = ""
    source_count: int = 0
    # Client local calendar date YYYY-MM-DD (recommended).
    study_date: str | None = None
