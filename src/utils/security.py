"""FastAPI dependencies for protecting farmer endpoints with access tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.repositories.session_repository import SessionRepository
from src.utils.auth import verify_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedFarmer:
    """Identity established from a valid, active access-token session."""

    farmer_id: int
    session_id: str


def get_current_farmer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedFarmer:
    """Require ``Authorization: Bearer <access_token>`` on a protected route."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid Bearer access token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise unauthorized

    try:
        farmer_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise unauthorized

    session = SessionRepository(db).get_by_access_token(credentials.credentials)
    if (
        not session
        or session.farmer_id != farmer_id
        or session.access_token_expires_at < datetime.utcnow()
    ):
        raise unauthorized

    return AuthenticatedFarmer(farmer_id=farmer_id, session_id=session.session_id)


def require_farmer_access(requested_farmer_id: int, current: AuthenticatedFarmer) -> None:
    """Reject requests attempting to act as another farmer."""
    if requested_farmer_id != current.farmer_id:
        raise HTTPException(status_code=403, detail="You may only access your own farmer data")
