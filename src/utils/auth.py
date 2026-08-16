"""Password hashing and authentication utilities."""

import hashlib
import secrets

# Static OTP for email verification during onboarding
STATIC_OTP = "123456"


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
