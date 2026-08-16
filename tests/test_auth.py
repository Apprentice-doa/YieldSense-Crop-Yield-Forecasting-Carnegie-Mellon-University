"""Integration tests for authentication and login flow."""

from fastapi.testclient import TestClient
import random
import time
from src.main import app

client = TestClient(app)


def create_and_verify_farmer(email: str = None, password: str = "TestPassword123") -> int:
    """Helper to create and verify a farmer account."""
    if email is None:
        email = f"auth_test{random.randint(100000, 999999)}@example.com"
    
    phone = f"+2547{random.randint(10000000, 99999999)}"
    
    # Signup
    signup_payload = {
        "name": "Test Farmer",
        "farm_country": "Kenya",
        "farm_state_region": "Central",
        "phone_number": phone,
        "email_address": email,
        "area_of_farmland": 2.0,
        "password": password,
        "crop_profiles": [
            {
                "crop_type": "Maize",
                "planting_month": "April",
                "harvest_month": "August",
                "average_yield_tons": 2.0
            }
        ]
    }
    
    r = client.post("/onboarding/signup", json=signup_payload)
    farmer_id = r.json()["id"]
    
    # Verify email with OTP
    verify_payload = {"farmer_id": farmer_id, "otp": "123456"}
    client.post("/onboarding/verify-email", json=verify_payload)
    
    return farmer_id


def test_login_success():
    """Test successful login with correct credentials."""
    print("\n[Test] Login with correct credentials...")
    
    email = f"login_test{random.randint(100000, 999999)}@example.com"
    password = "SecurePass123"
    farmer_id = create_and_verify_farmer(email, password)
    
    # Login
    login_payload = {"email_address": email, "password": password}
    r = client.post("/auth/login", json=login_payload)
    
    assert r.status_code == 200, f"Login failed: {r.text}"
    
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "session_id" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 30 * 60  # 30 minutes in seconds
    
    session_id = data["session_id"]
    print(f"✓ Login successful | Session: {session_id[:8]}... | Access expires in: {data['expires_in']}s")
    
    return session_id, data["refresh_token"]


def test_login_invalid_credentials():
    """Test login with incorrect credentials."""
    print("\n[Test] Login with invalid credentials...")
    
    email = f"invalid_test{random.randint(100000, 999999)}@example.com"
    create_and_verify_farmer(email, "CorrectPass123")
    
    # Try login with wrong password
    login_payload = {"email_address": email, "password": "WrongPassword123"}
    r = client.post("/auth/login", json=login_payload)
    
    assert r.status_code == 401
    assert "invalid" in r.json()["detail"].lower()
    
    print("✓ Invalid credentials properly rejected")


def test_login_unverified_farmer():
    """Test login with unverified farmer account."""
    print("\n[Test] Login with unverified farmer (no OTP)...")
    
    email = f"unverified_test{random.randint(100000, 999999)}@example.com"
    password = "TestPass123"
    
    # Signup but DON'T verify with OTP
    signup_payload = {
        "name": "Unverified Farmer",
        "farm_country": "Kenya",
        "farm_state_region": "Rift Valley",
        "phone_number": f"+2547{random.randint(10000000, 99999999)}",
        "email_address": email,
        "area_of_farmland": 1.5,
        "password": password,
        "crop_profiles": [
            {
                "crop_type": "Beans",
                "planting_month": "May",
                "harvest_month": "September",
                "average_yield_tons": 1.0
            }
        ]
    }
    
    client.post("/onboarding/signup", json=signup_payload)
    
    # Try to login without verifying
    login_payload = {"email_address": email, "password": password}
    r = client.post("/auth/login", json=login_payload)
    
    assert r.status_code == 403
    assert "verified" in r.json()["detail"].lower()
    
    print("✓ Unverified farmer login blocked")


def test_refresh_token():
    """Test refreshing access token with refresh token."""
    print("\n[Test] Refresh access token...")
    
    _, refresh_token = test_login_success()
    
    # Refresh
    refresh_payload = {"refresh_token": refresh_token}
    r = client.post("/auth/refresh", json=refresh_payload)
    
    assert r.status_code == 200, f"Refresh failed: {r.text}"
    
    data = r.json()
    assert "access_token" in data
    assert data["refresh_token"] == refresh_token
    assert data["token_type"] == "Bearer"
    
    print(f"✓ Token refreshed successfully | New access token: {data['access_token'][:20]}...")
    
    return data["access_token"]


def test_refresh_invalid_token():
    """Test refresh with invalid refresh token."""
    print("\n[Test] Refresh with invalid token...")
    
    refresh_payload = {"refresh_token": "invalid_token_xyz"}
    r = client.post("/auth/refresh", json=refresh_payload)
    
    assert r.status_code == 401
    assert "invalid" in r.json()["detail"].lower()
    
    print("✓ Invalid refresh token rejected")


def test_logout():
    """Test logout functionality."""
    print("\n[Test] Logout and deactivate session...")
    
    session_id, _ = test_login_success()
    
    # Logout
    r = client.post(f"/auth/logout?session_id={session_id}")
    
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    
    print(f"✓ Logged out successfully | Session: {session_id[:8]}... deactivated")


def test_session_status():
    """Test checking session status."""
    print("\n[Test] Check session status...")
    
    session_id, _ = test_login_success()
    
    # Check status
    r = client.get(f"/auth/session/{session_id}")
    
    assert r.status_code == 200
    
    data = r.json()
    assert data["session_id"] == session_id
    assert data["is_active"] == True
    assert "access_token_expires_at" in data
    
    print(f"✓ Session active | Expires at: {data['access_token_expires_at']}")
    
    # Logout and check status again
    client.post(f"/auth/logout?session_id={session_id}")
    r2 = client.get(f"/auth/session/{session_id}")
    
    assert r2.status_code == 200
    assert r2.json()["is_active"] == False
    
    print(f"✓ Session deactivated after logout")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AUTH INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_login_success()
        test_login_invalid_credentials()
        test_login_unverified_farmer()
        test_refresh_token()
        test_refresh_invalid_token()
        test_logout()
        test_session_status()
        
        print("\n" + "=" * 60)
        print("  ✓ ALL TESTS PASSED")
        print("=" * 60 + "\n")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
