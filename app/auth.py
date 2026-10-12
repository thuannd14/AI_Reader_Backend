"""API key authentication.

Accepts the key in either place:
    X-API-Key: <key>
    Authorization: Bearer <key>

If no keys are configured (API_KEYS empty), auth is disabled.

Uses fastapi.security.APIKeyHeader so the key scheme also appears in the
OpenAPI docs and Swagger UI shows an "Authorize" button.
"""
from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader

from .config import API_KEYS

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    x_api_key: str | None = Depends(_api_key_header),
    authorization: str | None = Header(default=None),
) -> None:
    if not API_KEYS:
        return  # auth disabled

    provided = x_api_key
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()

    if provided and any(secrets.compare_digest(provided, key) for key in API_KEYS):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "X-API-Key"},
    )
