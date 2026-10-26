"""Database models.

Tables:
    * Source          - one imported document (file name, language, level).
    * Vocabulary      - one word/phrase, linked to its Source via `source_id`.
    * UserProgress    - per-user continue-lesson pointer + study streak.
    * LearningWord    - per-user saved flashcard words (Chieng).
    * ChatSession     - per-user AI tutor conversation session (Chieng logs).
    * ChatLogMessage  - one user/assistant turn stored for a session.

(The FK is handled explicitly in the code rather than via ORM relationships,
which keeps the models simple and portable across databases.)
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, Text
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


class UserProgress(SQLModel, table=True):
    """Per-user continue-lesson pointer + consecutive study-day streak."""

    user_id: str = Field(primary_key=True, max_length=128)
    current_source_id: int | None = Field(default=None, index=True)
    current_source_name: str = Field(default="")
    current_source_language: str = Field(default="")
    current_source_level: str = Field(default="")
    current_source_count: int = Field(default=0)
    streak_count: int = Field(default=0)
    last_study_date: str = Field(default="")  # YYYY-MM-DD
    updated_at: datetime = Field(default_factory=_utcnow)


class LearningWord(SQLModel, table=True):
    """Per-user saved vocabulary word for flashcard practice (Chieng)."""

    user_id: str = Field(primary_key=True, max_length=128, index=True)
    word_id: int = Field(primary_key=True, index=True)
    word: str = Field(default="")
    traditional: str = Field(default="")
    language: str = Field(default="")
    level: str = Field(default="")
    pos: str = Field(default="")
    ipa: str = Field(default="")
    definition_en: str = Field(default="")
    meaning_vi: str = Field(default="")
    example: str = Field(default="")
    source_id: int | None = Field(default=None)
    status: str = Field(default="LEARNING", index=True)  # LEARNING|KNOWN|REVIEW
    # Epoch millis must be BIGINT — Postgres INTEGER overflows (~2e9).
    added_at_epoch_ms: int = Field(default=0, sa_column=Column(BigInteger(), nullable=False, default=0))
    updated_at_epoch_ms: int = Field(
        default=0,
        sa_column=Column(BigInteger(), nullable=False, default=0, index=True),
    )


class ChatSession(SQLModel, table=True):
    """One spoken/typed AI tutor conversation for a Chieng user."""

    id: str = Field(primary_key=True, max_length=64)
    user_id: str = Field(index=True, max_length=128)
    locale: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ChatLogMessage(SQLModel, table=True):
    """One turn (user STT/text or assistant DeepSeek reply) persisted on Railway."""

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, max_length=64, foreign_key="chatsession.id")
    user_id: str = Field(index=True, max_length=128)
    role: str = Field(index=True, max_length=16)  # user | assistant
    content: str = Field(default="", sa_column=Column(Text(), nullable=False))
    model: str = Field(default="")
    locale: str = Field(default="")
    client_message_id: str = Field(default="", max_length=128, index=True)
    created_at_epoch_ms: int = Field(
        default=0,
        sa_column=Column(BigInteger(), nullable=False, default=0, index=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
