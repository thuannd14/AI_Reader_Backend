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
