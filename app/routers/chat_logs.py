"""/chat-logs — persist Chieng AI tutor turns (STT + DeepSeek replies).

App calls DeepSeek directly; Railway only stores conversation history.

Routes:
    POST /chat-logs/{user_id}/sessions
    POST /chat-logs/{user_id}/messages
    GET  /chat-logs/{user_id}/sessions
    GET  /chat-logs/{user_id}/sessions/{session_id}/messages
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, func, select

from ..auth import require_api_key
from ..db import get_session
from ..models import ChatLogMessage, ChatSession
from ..schemas import (
    ChatLogMessageCreate,
    ChatLogMessageListOut,
    ChatLogMessageOut,
    ChatSessionCreate,
    ChatSessionListOut,
    ChatSessionOut,
)

router = APIRouter(tags=["chat-logs"], dependencies=[Depends(require_api_key)])

_ALLOWED_ROLES = {"user", "assistant"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _require_user_id(user_id: str) -> str:
    value = user_id.strip()
    if not value:
        raise HTTPException(status_code=400, detail="user_id is required")
    return value


def _session_out(session: Session, row: ChatSession) -> ChatSessionOut:
    count = session.exec(
        select(func.count()).select_from(ChatLogMessage).where(
            ChatLogMessage.session_id == row.id,
            ChatLogMessage.user_id == row.user_id,
        )
    ).one()
    return ChatSessionOut(
        id=row.id,
        user_id=row.user_id,
        locale=row.locale or "",
        created_at_epoch_ms=_epoch_ms(row.created_at) if row.created_at else 0,
        message_count=int(count or 0),
    )


def _message_out(row: ChatLogMessage) -> ChatLogMessageOut:
    return ChatLogMessageOut(
        id=int(row.id or 0),
        session_id=row.session_id,
        user_id=row.user_id,
        role=row.role,
        content=row.content or "",
        model=row.model or "",
        locale=row.locale or "",
        client_message_id=row.client_message_id or "",
        created_at_epoch_ms=int(row.created_at_epoch_ms or 0),
    )


@router.post("/chat-logs/{user_id}/sessions", response_model=ChatSessionOut)
def create_session(
    user_id: str,
    body: ChatSessionCreate,
    session: Session = Depends(get_session),
) -> ChatSessionOut:
    user_id = _require_user_id(user_id)
    now = _utcnow()
    row = ChatSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        locale=(body.locale or "").strip(),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _session_out(session, row)


@router.post("/chat-logs/{user_id}/messages", response_model=ChatLogMessageOut)
def append_message(
    user_id: str,
    body: ChatLogMessageCreate,
    session: Session = Depends(get_session),
) -> ChatLogMessageOut:
    user_id = _require_user_id(user_id)
    session_id = (body.session_id or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    role = (body.role or "").strip().lower()
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="role must be 'user' or 'assistant'")

    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    chat_session = session.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    client_message_id = (body.client_message_id or "").strip()
    if client_message_id:
        existing = session.exec(
            select(ChatLogMessage).where(
                ChatLogMessage.user_id == user_id,
                ChatLogMessage.client_message_id == client_message_id,
            )
        ).first()
        if existing:
            return _message_out(existing)

    epoch_ms = int(body.created_at_epoch_ms or 0)
    if epoch_ms <= 0:
        epoch_ms = int(_utcnow().timestamp() * 1000)

    row = ChatLogMessage(
        session_id=session_id,
        user_id=user_id,
        role=role,
        content=content,
        model=(body.model or "").strip(),
        locale=(body.locale or "").strip() or (chat_session.locale or ""),
        client_message_id=client_message_id,
        created_at_epoch_ms=epoch_ms,
        created_at=_utcnow(),
    )
    chat_session.updated_at = _utcnow()
    session.add(row)
    session.add(chat_session)
    session.commit()
    session.refresh(row)
    return _message_out(row)


@router.get("/chat-logs/{user_id}/sessions", response_model=ChatSessionListOut)
def list_sessions(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> ChatSessionListOut:
    user_id = _require_user_id(user_id)
    rows = session.exec(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(col(ChatSession.created_at).desc())
        .limit(limit)
    ).all()
    return ChatSessionListOut(items=[_session_out(session, row) for row in rows])


@router.get(
    "/chat-logs/{user_id}/sessions/{session_id}/messages",
    response_model=ChatLogMessageListOut,
)
def list_messages(
    user_id: str,
    session_id: str,
    session: Session = Depends(get_session),
) -> ChatLogMessageListOut:
    user_id = _require_user_id(user_id)
    session_id = session_id.strip()
    chat_session = session.get(ChatSession, session_id)
    if not chat_session or chat_session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    rows = session.exec(
        select(ChatLogMessage)
        .where(
            ChatLogMessage.user_id == user_id,
            ChatLogMessage.session_id == session_id,
        )
        .order_by(col(ChatLogMessage.created_at_epoch_ms).asc(), col(ChatLogMessage.id).asc())
    ).all()
    return ChatLogMessageListOut(items=[_message_out(row) for row in rows])
