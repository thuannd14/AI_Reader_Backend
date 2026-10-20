"""/progress — continue-lesson pointer + study streak (matches Android app).

Routes the app already calls:
    GET  /progress/{user_id}
    PUT  /progress/{user_id}
    POST /progress/{user_id}/check-in
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import require_api_key
from ..db import get_session
from ..models import Source, UserProgress
from ..schemas import ProgressOut, ProgressUpsert, StudyCheckIn

router = APIRouter(tags=["progress"], dependencies=[Depends(require_api_key)])


def _utc_today_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _parse_day(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _apply_streak(row: UserProgress, study_day: date) -> None:
    last = _parse_day(row.last_study_date)
    day_str = study_day.isoformat()
    if last == study_day:
        return
    if last == study_day - timedelta(days=1):
        row.streak_count = (row.streak_count or 0) + 1
    else:
        row.streak_count = 1
    row.last_study_date = day_str


def _fill_source_from_db(session: Session, source_id: int, row: UserProgress) -> None:
    src = session.get(Source, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    row.current_source_id = src.id
    if not row.current_source_name:
        row.current_source_name = src.name
    if not row.current_source_language:
        row.current_source_language = src.language
    if not row.current_source_level:
        row.current_source_level = src.level
    if not row.current_source_count:
        row.current_source_count = src.count


def _get_or_create(session: Session, user_id: str) -> UserProgress:
    row = session.get(UserProgress, user_id)
    if not row:
        row = UserProgress(user_id=user_id)
        session.add(row)
    return row


def _to_out(row: UserProgress) -> ProgressOut:
    return ProgressOut.model_validate(row, from_attributes=True)


@router.get("/progress/{user_id}", response_model=ProgressOut)
def get_progress(user_id: str, session: Session = Depends(get_session)) -> ProgressOut:
    row = session.get(UserProgress, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Progress not found")
    return _to_out(row)


@router.put("/progress/{user_id}", response_model=ProgressOut)
def upsert_progress(
    user_id: str,
    body: ProgressUpsert,
    session: Session = Depends(get_session),
) -> ProgressOut:
    user_id = user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    row = _get_or_create(session, user_id)

    if body.current_source_id is not None:
        src = session.get(Source, body.current_source_id)
        if not src:
            raise HTTPException(status_code=404, detail="Source not found")
        row.current_source_id = body.current_source_id
        row.current_source_name = body.current_source_name or src.name
        row.current_source_language = body.current_source_language or src.language
        row.current_source_level = body.current_source_level or src.level
        row.current_source_count = (
            body.current_source_count if body.current_source_count else src.count
        )
    else:
        if body.current_source_name:
            row.current_source_name = body.current_source_name
        if body.current_source_language:
            row.current_source_language = body.current_source_language
        if body.current_source_level:
            row.current_source_level = body.current_source_level
        if body.current_source_count:
            row.current_source_count = body.current_source_count

    if body.streak_count is not None:
        row.streak_count = max(0, body.streak_count)
    if body.last_study_date:
        if _parse_day(body.last_study_date) is None:
            raise HTTPException(status_code=400, detail="Invalid last_study_date")
        row.last_study_date = body.last_study_date.strip()[:10]

    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_out(row)


@router.post("/progress/{user_id}/check-in", response_model=ProgressOut)
def check_in(
    user_id: str,
    body: StudyCheckIn,
    session: Session = Depends(get_session),
) -> ProgressOut:
    """Mark today's study for a lesson: set continue pointer + bump streak."""
    user_id = user_id.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    study_day = _parse_day(body.study_date) or datetime.now(timezone.utc).date()
    row = _get_or_create(session, user_id)

    row.current_source_id = body.source_id
    row.current_source_name = body.source_name
    row.current_source_language = body.source_language
    row.current_source_level = body.source_level
    row.current_source_count = body.source_count
    _fill_source_from_db(session, body.source_id, row)

    _apply_streak(row, study_day)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_out(row)
