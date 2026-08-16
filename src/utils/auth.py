"""Password hashing and authentication utilities."""

import hashlib
import secrets
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Static OTP for email verification during onboarding
STATIC_OTP = "123456"

# JWT secret key (in production, load from environment)
JWT_SECRET_KEY = secrets.token_urlsafe(32)

# Token expiry times (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2.
    
    Format: algorithm$iterations$salt$hash
    """
    salt = secrets.token_hex(32)
    iterations = 100000
    # Use PBKDF2 with SHA256
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), iterations)
    hash_hex = hash_obj.hex()
    return f"pbkdf2_sha256${iterations}${salt}${hash_hex}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against its hash.
    
    Expected format: pbkdf2_sha256$iterations$salt$hash
    """
    try:
        parts = password_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        
        iterations = int(parts[1])
        salt = parts[2]
        stored_hash = parts[3]
        
        # Recompute hash with the stored salt and iterations
        hash_obj = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode(), iterations)
        computed_hash = hash_obj.hex()
        
        return computed_hash == stored_hash
    except Exception:
        return False


def verify_otp(provided_otp: str) -> bool:
    """Verify the provided OTP against the static OTP."""
    return provided_otp == STATIC_OTP


def _base64_url_encode(data: bytes) -> str:
    """Encode bytes to base64url format (JWT standard)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64_url_decode(data: str) -> bytes:
    """Decode base64url format to bytes (JWT standard)."""
    # Add padding if needed
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def _create_jwt_signature(header: str, payload: str, secret: str) -> str:
    """Create HMAC-SHA256 signature for JWT."""
    import hmac
    message = f"{header}.{payload}".encode("utf-8")
    signature_bytes = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    return _base64_url_encode(signature_bytes)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
    """Create a JWT access token.
    
    Returns:
        Tuple of (token_string, expiry_datetime)
    """
    import hmac
    
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.utcnow()
    expiry = now + expires_delta
    
    # JWT Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_encoded = _base64_url_encode(json.dumps(header).encode())
    
    # JWT Payload
    payload = {
        **data,
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp())
    }
    payload_encoded = _base64_url_encode(json.dumps(payload).encode())
    
    # Signature
    message = f"{header_encoded}.{payload_encoded}".encode()
    signature = hmac.new(JWT_SECRET_KEY.encode(), message, hashlib.sha256).digest()
    signature_encoded = _base64_url_encode(signature)
    
    token = f"{header_encoded}.{payload_encoded}.{signature_encoded}"
    return token, expiry


def create_refresh_token() -> tuple[str, datetime]:
    """Create a refresh token.
    
    Returns:
        Tuple of (token_string, expiry_datetime)
    """
    expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expiry = datetime.utcnow() + expires_delta
    
    # Generate a long random token for refresh
    token = secrets.token_urlsafe(64)
    return token, expiry


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT access token.
    
    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    import hmac
    
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        # Verify signature
        message = f"{header_encoded}.{payload_encoded}".encode()
        expected_signature = hmac.new(JWT_SECRET_KEY.encode(), message, hashlib.sha256).digest()
        expected_signature_encoded = _base64_url_encode(expected_signature)
        
        if signature_encoded != expected_signature_encoded:
            return None
        
        # Decode payload
        payload_json = _base64_url_decode(payload_encoded)
        payload = json.loads(payload_json)
        
        # Check expiry
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        
        return payload
    except Exception:
        return None
