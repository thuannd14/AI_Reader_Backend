"""/sources endpoints: list documents that have been imported."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select

from ..db import get_session
from ..models import Source, Vocabulary
from ..schemas import SourceOut

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceOut])
def list_sources(session: Session = Depends(get_session)) -> list[SourceOut]:
    items = session.exec(select(Source).order_by(Source.imported_at.desc())).all()
    return [SourceOut.model_validate(item, from_attributes=True) for item in items]


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, session: Session = Depends(get_session)) -> dict:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    session.exec(delete(Vocabulary).where(Vocabulary.source_id == source_id))
    session.delete(source)
    session.commit()
    return {"deleted": source_id}
