"""/learning-words — saved flashcard words per user (Chieng app).

Routes:
    GET    /learning-words/{user_id}
    PUT    /learning-words/{user_id}              (upsert batch)
    PUT    /learning-words/{user_id}/{word_id}    (upsert one)
    DELETE /learning-words/{user_id}/{word_id}
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..db import get_session
from ..models import LearningWord
from ..schemas import LearningWordOut, LearningWordUpsert, LearningWordsListOut, LearningWordsUpsertBatch

router = APIRouter(tags=["learning-words"], dependencies=[Depends(require_api_key)])

_ALLOWED_STATUS = {"LEARNING", "KNOWN", "REVIEW"}


def _to_out(row: LearningWord) -> LearningWordOut:
    return LearningWordOut.model_validate(row, from_attributes=True)


def _apply_upsert(row: LearningWord, body: LearningWordUpsert, word_id: int) -> None:
    status = (body.status or "LEARNING").strip().upper()
    if status not in _ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    row.word_id = word_id
    row.word = body.word
    row.traditional = body.traditional
    row.language = body.language
    row.level = body.level
    row.pos = body.pos
    row.ipa = body.ipa
    row.definition_en = body.definition_en
    row.meaning_vi = body.meaning_vi
    row.example = body.example
    row.source_id = body.source_id
    row.status = status
    if body.added_at_epoch_ms:
        row.added_at_epoch_ms = body.added_at_epoch_ms
    row.updated_at_epoch_ms = body.updated_at_epoch_ms or int(
        datetime.now(timezone.utc).timestamp() * 1000
    )


@router.get("/learning-words/{user_id}", response_model=LearningWordsListOut)
def list_learning_words(user_id: str, session: Session = Depends(get_session)) -> LearningWordsListOut:
    user_id = user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    rows = session.exec(
        select(LearningWord)
        .where(LearningWord.user_id == user_id)
        .order_by(LearningWord.updated_at_epoch_ms.desc())
    ).all()
    return LearningWordsListOut(items=[_to_out(r) for r in rows])


@router.put("/learning-words/{user_id}", response_model=LearningWordsListOut)
def upsert_learning_words_batch(
    user_id: str,
    body: LearningWordsUpsertBatch,
    session: Session = Depends(get_session),
) -> LearningWordsListOut:
    """Upsert many words (last-write-wins per word_id by updated_at_epoch_ms)."""
    user_id = user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    for item in body.items:
        word_id = item.word_id
        if word_id is None or word_id <= 0:
            raise HTTPException(status_code=400, detail="Each item needs a positive word_id")
        existing = session.get(LearningWord, (user_id, word_id))
        incoming_ts = item.updated_at_epoch_ms or 0
        if existing and existing.updated_at_epoch_ms > incoming_ts:
            continue
        row = existing or LearningWord(user_id=user_id, word_id=word_id)
        if not existing:
            row.added_at_epoch_ms = item.added_at_epoch_ms or incoming_ts
        _apply_upsert(row, item, word_id)
        session.add(row)

    session.commit()
    rows = session.exec(
        select(LearningWord)
        .where(LearningWord.user_id == user_id)
        .order_by(LearningWord.updated_at_epoch_ms.desc())
    ).all()
    return LearningWordsListOut(items=[_to_out(r) for r in rows])


@router.put("/learning-words/{user_id}/{word_id}", response_model=LearningWordOut)
def upsert_learning_word(
    user_id: str,
    word_id: int,
    body: LearningWordUpsert,
    session: Session = Depends(get_session),
) -> LearningWordOut:
    user_id = user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if word_id <= 0:
        raise HTTPException(status_code=400, detail="word_id must be positive")

    existing = session.get(LearningWord, (user_id, word_id))
    incoming_ts = body.updated_at_epoch_ms or 0
    if existing and existing.updated_at_epoch_ms > incoming_ts:
        return _to_out(existing)

    row = existing or LearningWord(user_id=user_id, word_id=word_id)
    if not existing:
        row.added_at_epoch_ms = body.added_at_epoch_ms or incoming_ts
    _apply_upsert(row, body, word_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_out(row)


@router.delete("/learning-words/{user_id}/{word_id}")
def delete_learning_word(
    user_id: str,
    word_id: int,
    session: Session = Depends(get_session),
) -> dict:
    user_id = user_id.strip()
    row = session.get(LearningWord, (user_id, word_id))
    if not row:
        raise HTTPException(status_code=404, detail="Learning word not found")
    session.delete(row)
    session.commit()
    return {"ok": True, "user_id": user_id, "word_id": word_id}
