"""/progress — save & load per-device study state (current lesson + streak)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..db import get_session
from ..models import Source, StudyProgress, Vocabulary
from ..schemas import ProgressOut, ProgressUpdate

router = APIRouter(tags=["progress"], dependencies=[Depends(require_api_key)])


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _apply_streak(progress: StudyProgress, study_day: date) -> None:
    """Update streak_days / last_study_date for a study event on ``study_day``."""
    last = progress.last_study_date
    if last == study_day:
        return  # already counted today
    if last == study_day - timedelta(days=1):
        progress.streak_days = (progress.streak_days or 0) + 1
    else:
        progress.streak_days = 1
    progress.last_study_date = study_day


def _to_out(row: StudyProgress) -> ProgressOut:
    return ProgressOut.model_validate(row, from_attributes=True)


@router.get("/progress/{device_id}", response_model=ProgressOut)
def get_progress(device_id: str, session: Session = Depends(get_session)) -> ProgressOut:
    row = session.exec(
        select(StudyProgress).where(StudyProgress.device_id == device_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Progress not found")
    return _to_out(row)


@router.put("/progress", response_model=ProgressOut)
def upsert_progress(
    body: ProgressUpdate, session: Session = Depends(get_session)
) -> ProgressOut:
    device_id = body.device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")

    if body.source_id is not None and not session.get(Source, body.source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    if body.word_id is not None and not session.get(Vocabulary, body.word_id):
        raise HTTPException(status_code=404, detail="Word not found")

    row = session.exec(
        select(StudyProgress).where(StudyProgress.device_id == device_id)
    ).first()
    if not row:
        row = StudyProgress(device_id=device_id, streak_days=0)
        session.add(row)

    if body.source_id is not None:
        row.source_id = body.source_id
    if body.word_id is not None:
        row.word_id = body.word_id

    if body.record_study:
        _apply_streak(row, body.study_date or _utc_today())

    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_out(row)
