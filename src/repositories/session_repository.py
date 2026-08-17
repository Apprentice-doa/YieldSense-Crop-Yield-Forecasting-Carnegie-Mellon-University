"""Repository for managing farmer sessions."""

from __future__ import annotations

from sqlalchemy.orm import Session
from typing import Optional

from src.db.models.session import FarmerSession


class SessionRepository:
    """Data access layer for farmer sessions."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, session: FarmerSession) -> FarmerSession:
        """Create a new session record."""
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_session_id(self, session_id: str) -> Optional[FarmerSession]:
        """Get session by session ID (GUID)."""
        return self.db.query(FarmerSession).filter(FarmerSession.session_id == session_id).first()

    def get_by_refresh_token(self, refresh_token: str) -> Optional[FarmerSession]:
        """Get session by refresh token."""
        return self.db.query(FarmerSession).filter(
            FarmerSession.refresh_token == refresh_token,
            FarmerSession.is_active == True
        ).first()

    def get_by_access_token(self, access_token: str) -> Optional[FarmerSession]:
        """Return the active session that currently owns an access token."""
        return self.db.query(FarmerSession).filter(
            FarmerSession.access_token == access_token,
            FarmerSession.is_active.is_(True),
        ).first()

    def get_active_sessions_for_farmer(self, farmer_id: int) -> list[FarmerSession]:
        """Get all active sessions for a farmer."""
        return self.db.query(FarmerSession).filter(
            FarmerSession.farmer_id == farmer_id,
            FarmerSession.is_active == True
        ).all()

    def deactivate_session(self, session: FarmerSession) -> None:
        """Deactivate a session."""
        session.is_active = False
        self.db.flush()

    def delete(self, session: FarmerSession) -> None:
        """Delete a session."""
        self.db.delete(session)

    def commit(self) -> None:
        """Commit transaction."""
        self.db.commit()
