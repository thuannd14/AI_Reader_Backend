"""/words endpoints: list, search, and fetch a single entry."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from ..db import get_session
from ..models import Source, Vocabulary
from ..schemas import Stats, WordOut, WordPage

router = APIRouter(tags=["words"])


@router.get("/words", response_model=WordPage)
def list_words(
    lang: str | None = Query(None, description='Language: "en" or "zh"'),
    level: str | None = Query(None, description='Level e.g. "B1" or "HSK3"'),
    q: str | None = Query(None, description="Search in word / meaning / definition"),
    source_id: int | None = Query(None),
    order: str = Query("level", pattern="^(level|word|recent)$"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> WordPage:
    conditions = []
    if lang:
        conditions.append(Vocabulary.language == lang)
    if level:
        conditions.append(Vocabulary.level == level)
    if source_id:
        conditions.append(Vocabulary.source_id == source_id)
    if q:
        like = f"%{q}%"
        conditions.append(
            (Vocabulary.word.like(like))
            | (Vocabulary.meaning_vi.like(like))
            | (Vocabulary.definition_en.like(like))
        )

    count_stmt = select(func.count()).select_from(Vocabulary)
    stmt = select(Vocabulary)
    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        stmt = stmt.where(condition)

    if order == "word":
        stmt = stmt.order_by(Vocabulary.word)
    elif order == "recent":
        stmt = stmt.order_by(Vocabulary.created_at.desc())
    else:
        stmt = stmt.order_by(Vocabulary.level, Vocabulary.word)

    total = session.exec(count_stmt).one()
    items = session.exec(stmt.offset(offset).limit(limit)).all()
    return WordPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[WordOut.model_validate(item, from_attributes=True) for item in items],
    )


@router.get("/words/{word_id}", response_model=WordOut)
def get_word(word_id: int, session: Session = Depends(get_session)) -> WordOut:
    item = session.get(Vocabulary, word_id)
    if not item:
        raise HTTPException(status_code=404, detail="Word not found")
    return WordOut.model_validate(item, from_attributes=True)


@router.get("/stats", response_model=Stats)
def stats(session: Session = Depends(get_session)) -> Stats:
    total_words = session.exec(select(func.count()).select_from(Vocabulary)).one()
    total_sources = session.exec(select(func.count()).select_from(Source)).one()
    languages = {
        row[0]: row[1]
        for row in session.exec(
            select(Vocabulary.language, func.count()).group_by(Vocabulary.language)
        ).all()
    }
    levels = {
        row[0]: row[1]
        for row in session.exec(
            select(Vocabulary.level, func.count()).group_by(Vocabulary.level)
        ).all()
    }
    return Stats(
        total_words=total_words,
        total_sources=total_sources,
        languages=languages,
        levels=levels,
    )
