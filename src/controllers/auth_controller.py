"""Authentication controller for login and token management."""

from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.auth_service import AuthService
from src.utils.security import AuthenticatedFarmer, get_current_farmer
from src.schemas.auth_schema import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    SessionStatusResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_client_ip(x_forwarded_for: str = Header(None)) -> str | None:
    """Extract client IP from headers."""
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return None


def get_user_agent(user_agent: str = Header(None)) -> str | None:
    """Extract user agent from headers."""
    return user_agent


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    x_forwarded_for: str = Header(None),
    user_agent: str = Header(None),
) -> TokenResponse:
    """Login with email and password.
    
    - Email and password must be correct
    - Farmer account must be verified (onboarded and email confirmed with OTP)
    - Returns access token (expires in 30 minutes) and refresh token
    - Access token is JWT that can be used to authenticate requests
    """
    svc = AuthService(db)
    
    ip_address = get_client_ip(x_forwarded_for)
    
    try:
        result = svc.login(
            email=payload.email_address,
            password=payload.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        if str(e) == "farmer_not_verified":
            raise HTTPException(
                status_code=403,
                detail="Account not verified. Please complete onboarding with OTP verification."
            )
        raise

    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Refresh an expired access token.
    
    - Provide valid refresh token from login or previous refresh
    - Returns new access token with 30 minute expiry
    - Refresh token remains valid for 7 days
    """
    svc = AuthService(db)
    result = svc.refresh_access_token(payload.refresh_token)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return TokenResponse(**result)


@router.post("/logout")
async def logout(
    session_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> dict:
    """Logout and deactivate the current session.
    
    - Invalidates the current access token
    - Farmer will need to login again for new session
    """
    if session_id != current.session_id:
        raise HTTPException(status_code=403, detail="You may only log out your own session")

    svc = AuthService(db)
    ok = svc.logout(session_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "success", "message": "Logged out successfully"}


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> SessionStatusResponse:
    """Get the status of a session.
    
    - Check if session is active
    - See when access token expires
    """
    if session_id != current.session_id:
        raise HTTPException(status_code=403, detail="You may only view your own session")

    svc = AuthService(db)
    status = svc.get_session_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatusResponse(**status)
