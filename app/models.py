"""Database models.

Tables:
    * Source        - one imported document (file name, language, level).
    * Vocabulary    - one word/phrase, linked to its Source via `source_id`.
    * StudyProgress - per-device learning state (current lesson + streak).

(The FK is handled explicitly in the code rather than via ORM relationships,
which keeps the models simple and portable across databases.)
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    language: str = Field(default="en", index=True)  # "en" | "zh"
    level: str = Field(default="", index=True)        # B1.., HSK3..
    count: int = Field(default=0)
    imported_at: datetime = Field(default_factory=_utcnow)


class Vocabulary(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    word: str = Field(index=True)
    traditional: str = Field(default="")
    language: str = Field(default="en", index=True)  # "en" | "zh"
    level: str = Field(default="", index=True)        # CEFR or HSK
    pos: str = Field(default="")
    ipa: str = Field(default="")                      # IPA or pinyin
    definition_en: str = Field(default="")
    meaning_vi: str = Field(default="")
    example: str = Field(default="")
    source_id: int | None = Field(default=None, foreign_key="source.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class StudyProgress(SQLModel, table=True):
    """One row per Android device / install."""

    id: int | None = Field(default=None, primary_key=True)
    device_id: str = Field(index=True, unique=True, max_length=128)
    source_id: int | None = Field(default=None, foreign_key="source.id", index=True)
    word_id: int | None = Field(default=None, index=True)
    streak_days: int = Field(default=0)
    last_study_date: date | None = Field(default=None, index=True)
    updated_at: datetime = Field(default_factory=_utcnow)
