"""Authentication service for handling login and token management."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.repositories.farmer_repository import FarmerRepository
from src.repositories.session_repository import SessionRepository
from src.db.models.session import FarmerSession
from src.utils.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


class AuthService:
    """Service for managing farmer authentication and sessions."""

    def __init__(self, db: Session):
        self.farmer_repo = FarmerRepository(db)
        self.session_repo = SessionRepository(db)
        self.db = db

    def login(
        self,
        password: str,
        email_address: str | None = None,
        phone_number: str | None = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> dict | None:
        """Authenticate a farmer and create a session.
        
        Args:
            email_address: Farmer email, if used to sign in
            phone_number: Farmer phone number, if used to sign in
            password: Plain text password
            ip_address: Optional IP address for logging
            user_agent: Optional user agent for logging
            
        Returns:
            Dictionary with tokens and session info, or None if auth fails
        """
        if bool(email_address) == bool(phone_number):
            return None

        farmer = (
            self.farmer_repo.find_by_email(email_address)
            if email_address
            else self.farmer_repo.find_by_phone(phone_number)
        )
        if not farmer:
            return None

        # Verify password
        if not verify_password(password, farmer.password_hash):
            return None

        # Check if farmer is verified
        if not farmer.is_verified:
            raise ValueError("farmer_not_verified")

        # Create access token
        access_token, access_expiry = create_access_token({
            "sub": str(farmer.id),
            "email": farmer.email_address,
            "name": farmer.name,
        })

        # Create refresh token
        refresh_token, refresh_expiry = create_refresh_token()

        # Generate session ID (GUID)
        session_id = str(uuid.uuid4())

        # Store session in database
        db_session = FarmerSession(
            farmer_id=farmer.id,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expiry,
            refresh_token_expires_at=refresh_expiry,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session_repo.create(db_session)
        self.session_repo.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            "session_id": session_id,
        }

    def refresh_access_token(self, refresh_token: str) -> dict | None:
        """Generate a new access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary with new access token and session info, or None if refresh fails
        """
        # Find session by refresh token
        session = self.session_repo.get_by_refresh_token(refresh_token)
        if not session:
            return None

        # Check if refresh token is not expired
        if session.refresh_token_expires_at < datetime.utcnow():
            self.session_repo.deactivate_session(session)
            self.session_repo.commit()
            return None

        # Get farmer details
        farmer = self.farmer_repo.get_by_id(session.farmer_id)
        if not farmer:
            return None

        # Create new access token
        new_access_token, new_access_expiry = create_access_token({
            "sub": str(farmer.id),
            "email": farmer.email_address,
            "name": farmer.name,
        })

        # Update session with new access token
        session.access_token = new_access_token
        session.access_token_expires_at = new_access_expiry
        self.db.flush()
        self.session_repo.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            "session_id": session.session_id,
        }

    def validate_access_token(self, token: str) -> dict | None:
        """Validate an access token and return its payload.
        
        Args:
            token: JWT access token
            
        Returns:
            Token payload if valid, None if invalid or expired
        """
        return verify_access_token(token)

    def logout(self, session_id: str) -> bool:
        """Deactivate a session (logout).
        
        Args:
            session_id: Session ID to logout
            
        Returns:
            True if logout successful, False if session not found
        """
        session = self.session_repo.get_by_session_id(session_id)
        if not session:
            return False

        self.session_repo.deactivate_session(session)
        self.session_repo.commit()
        return True

    def get_session_status(self, session_id: str) -> dict | None:
        """Get the status of a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session status dict or None if not found
        """
        session = self.session_repo.get_by_session_id(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "farmer_id": session.farmer_id,
            "is_active": session.is_active,
            "access_token_expires_at": session.access_token_expires_at,
            "created_at": session.created_at,
        }
