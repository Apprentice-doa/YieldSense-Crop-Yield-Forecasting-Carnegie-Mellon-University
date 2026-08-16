"""Integration tests for farmer onboarding flow."""

from fastapi.testclient import TestClient
import random
from src.main import app

client = TestClient(app)


def test_full_onboarding_flow():
    """Test complete onboarding flow: signup -> verify email -> check status."""
    
    # Step 1: Signup with farmer details and crop profiles
    phone = f"+2547{random.randint(10000000, 99999999)}"
    email = f"farmer{random.randint(10000, 99999)}@example.com"
    
    signup_payload = {
        "name": "John Mwangi",
        "farm_country": "Kenya",
        "farm_state_region": "Nairobi",
        "phone_number": phone,
        "email_address": email,
        "area_of_farmland": 2.5,
        "password": "SecurePassword123",
        "crop_profiles": [
            {
                "crop_type": "Maize",
                "planting_month": "April",
                "harvest_month": "August",
                "average_yield_tons": 2.0
            },
            {
                "crop_type": "Beans",
                "planting_month": "May",
                "harvest_month": "September",
                "average_yield_tons": 1.5
            }
        ]
    }
    
    # Signup
    r_signup = client.post("/onboarding/signup", json=signup_payload)
    assert r_signup.status_code == 200, f"Signup failed: {r_signup.text}"
    
    farmer_data = r_signup.json()
    farmer_id = farmer_data["id"]
    
    # Verify initial state
    assert farmer_data["is_verified"] == False
    assert farmer_data["otp_verified"] == False
    assert farmer_data["email_address"] == email
    assert farmer_data["phone_number"] == phone
    
    print(f"✓ Farmer created: ID={farmer_id}, Email={email}")
    
    # Step 2: Verify email with static OTP (123456)
    verify_payload = {
        "farmer_id": farmer_id,
        "otp": "123456"
    }
    
    r_verify = client.post("/onboarding/verify-email", json=verify_payload)
    assert r_verify.status_code == 200, f"Email verification failed: {r_verify.text}"
    
    verify_response = r_verify.json()
    assert verify_response["status"] == "success"
    assert verify_response["farmer_id"] == farmer_id
    
    print(f"✓ Email verified for farmer {farmer_id}")
    
    # Step 3: Check onboarding status
    r_status = client.get(f"/onboarding/status/{farmer_id}")
    assert r_status.status_code == 200
    
    status_data = r_status.json()
    assert status_data["is_verified"] == True
    assert status_data["otp_verified"] == True
    
    print(f"✓ Onboarding complete for farmer {farmer_id}")
    
    return farmer_id


def test_onboarding_duplicate_email():
    """Test that duplicate email is rejected."""
    email = f"duplicate{random.randint(10000, 99999)}@example.com"
    
    signup_payload = {
        "name": "Alice Kipchoge",
        "farm_country": "Kenya",
        "farm_state_region": "Rift Valley",
        "phone_number": f"+2547{random.randint(10000000, 99999999)}",
        "email_address": email,
        "area_of_farmland": 1.5,
        "password": "Password123!",
        "crop_profiles": [
            {
                "crop_type": "Wheat",
                "planting_month": "March",
                "harvest_month": "July",
                "average_yield_tons": 3.0
            }
        ]
    }
    
    # First signup should succeed
    r1 = client.post("/onboarding/signup", json=signup_payload)
    assert r1.status_code == 200
    
    # Second signup with same email should fail
    signup_payload["phone_number"] = f"+2547{random.randint(10000000, 99999999)}"
    r2 = client.post("/onboarding/signup", json=signup_payload)
    assert r2.status_code == 400
    assert "email" in r2.json()["detail"].lower()
    
    print("✓ Duplicate email properly rejected")


def test_invalid_otp():
    """Test that invalid OTP is rejected."""
    phone = f"+2547{random.randint(10000000, 99999999)}"
    email = f"otp_test{random.randint(10000, 99999)}@example.com"
    
    signup_payload = {
        "name": "Bob Smith",
        "farm_country": "Ghana",
        "farm_state_region": "Ashanti",
        "phone_number": phone,
        "email_address": email,
        "area_of_farmland": 2.0,
        "password": "TestPassword123",
        "crop_profiles": [
            {
                "crop_type": "Cocoa",
                "planting_month": "January",
                "harvest_month": "October",
                "average_yield_tons": 1.2
            }
        ]
    }
    
    r_signup = client.post("/onboarding/signup", json=signup_payload)
    assert r_signup.status_code == 200
    farmer_id = r_signup.json()["id"]
    
    # Try with wrong OTP
    verify_payload = {
        "farmer_id": farmer_id,
        "otp": "000000"
    }
    r_verify = client.post("/onboarding/verify-email", json=verify_payload)
    assert r_verify.status_code == 400
    assert "invalid" in r_verify.json()["detail"].lower()
    
    print("✓ Invalid OTP properly rejected")


if __name__ == "__main__":
    print("\n=== Running Onboarding Tests ===\n")
    test_full_onboarding_flow()
    print()
    test_onboarding_duplicate_email()
    print()
    test_invalid_otp()
    print("\n=== All Tests Passed ===\n")
