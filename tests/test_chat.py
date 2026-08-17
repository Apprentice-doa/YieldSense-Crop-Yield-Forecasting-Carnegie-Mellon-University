"""Integration tests for chat and conversation functionality."""

from fastapi.testclient import TestClient
import random
from src.main import app

client = TestClient(app)


def create_verified_farmer() -> int:
    """Helper to create and verify a farmer account."""
    email = f"chat_test{random.randint(100000, 999999)}@example.com"
    phone = f"+2547{random.randint(10000000, 99999999)}"
    
    # Signup
    signup_payload = {
        "name": "Chat Farmer",
        "farm_country": "Kenya",
        "farm_state_region": "Nairobi",
        "phone_number": phone,
        "email_address": email,
        "area_of_farmland": 2.0,
        "password": "TestPass123",
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
    
    # Verify with OTP
    verify_payload = {"phone_number": phone, "otp": "123456"}
    client.post("/onboarding/verify-email", json=verify_payload)
    
    return farmer_id


def test_create_conversation():
    """Test creating a new conversation."""
    print("\n[Test] Create conversation...")
    
    farmer_id = create_verified_farmer()
    
    payload = {
        "title": "Maize Yield Discussion",
        "description": "Discussing expected yield for current season",
        "context_type": "yield_prediction"
    }
    
    r = client.post(
        "/chat/conversations",
        json=payload,
        params={"farmer_id": farmer_id}
    )
    
    assert r.status_code == 200, f"Create conversation failed: {r.text}"
    data = r.json()
    
    assert data["title"] == "Maize Yield Discussion"
    assert data["context_type"] == "yield_prediction"
    assert data["is_active"] == "active"
    assert data["message_count"] == 0
    
    conversation_id = data["id"]
    print(f"✓ Conversation created | ID: {conversation_id} | Title: {data['title']}")
    
    return farmer_id, conversation_id


def test_send_message():
    """Test sending a message in a conversation."""
    print("\n[Test] Send message in conversation...")
    
    farmer_id, conversation_id = test_create_conversation()
    
    payload = {
        "content": "What yield should I expect this season?",
        "message_type": "text"
    }
    
    r = client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json=payload,
        params={"farmer_id": farmer_id}
    )
    
    assert r.status_code == 200, f"Send message failed: {r.text}"
    data = r.json()
    
    assert data["content"] == "What yield should I expect this season?"
    assert data["sender_type"] == "farmer"
    assert data["message_type"] == "text"
    assert data["is_read"] == "read"  # Farmer's own message is auto-read
    
    message_id = data["id"]
    print(f"✓ Message sent | ID: {message_id} | Content: {data['content'][:30]}...")
    
    return farmer_id, conversation_id, message_id


def test_get_conversation_messages():
    """Test retrieving all messages in a conversation."""
    print("\n[Test] Get conversation messages...")
    
    farmer_id, conversation_id = test_create_conversation()
    
    # Send a few messages
    for i in range(3):
        payload = {"content": f"Message {i+1}", "message_type": "text"}
        client.post(
            f"/chat/conversations/{conversation_id}/messages",
            json=payload,
            params={"farmer_id": farmer_id}
        )
    
    # Get conversation with all messages
    r = client.get(f"/chat/conversations/{conversation_id}")
    
    assert r.status_code == 200
    data = r.json()
    
    assert len(data["messages"]) == 3
    assert data["messages"][0]["content"] == "Message 1"
    assert data["messages"][-1]["content"] == "Message 3"
    
    print(f"✓ Retrieved conversation | Messages: {len(data['messages'])}")
    
    return farmer_id


def test_list_farmer_conversations():
    """Test listing all conversations for a farmer."""
    print("\n[Test] List farmer conversations...")
    
    farmer_id = create_verified_farmer()
    
    # Create multiple conversations
    for i in range(3):
        payload = {
            "title": f"Conversation {i+1}",
            "description": f"Test conversation {i+1}",
        }
        client.post(
            "/chat/conversations",
            json=payload,
            params={"farmer_id": farmer_id}
        )
    
    # List conversations
    r = client.get(
        "/chat/conversations",
        params={"farmer_id": farmer_id, "status": "active"}
    )
    
    assert r.status_code == 200
    data = r.json()
    
    assert len(data) == 3
    assert data[0]["title"] == "Conversation 1"
    
    print(f"✓ Listed conversations | Count: {len(data)}")


def test_mark_message_as_read():
    """Test marking a message as read."""
    print("\n[Test] Mark message as read...")
    
    farmer_id, conversation_id, message_id = test_send_message()
    
    # Mark as read
    r = client.post(
        f"/chat/conversations/{conversation_id}/messages/{message_id}/read"
    )
    
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    
    print(f"✓ Message marked as read | ID: {message_id}")


def test_unread_count():
    """Test getting unread message count."""
    print("\n[Test] Get unread message count...")
    
    farmer_id = create_verified_farmer()
    
    # Create conversation and send messages
    payload = {
        "title": "Test Conversation",
        "description": "For testing unread count"
    }
    
    r = client.post(
        "/chat/conversations",
        json=payload,
        params={"farmer_id": farmer_id}
    )
    conversation_id = r.json()["id"]
    
    # Get unread count (should be 0 initially)
    r = client.get(
        "/chat/unread-count",
        params={"farmer_id": farmer_id}
    )
    
    assert r.status_code == 200
    data = r.json()
    assert data["unread_count"] == 0
    
    print(f"✓ Unread count retrieved | Count: {data['unread_count']}")


def test_archive_conversation():
    """Test archiving a conversation."""
    print("\n[Test] Archive conversation...")
    
    farmer_id, conversation_id = test_create_conversation()
    
    # Archive
    r = client.post(
        f"/chat/conversations/{conversation_id}/archive"
    )
    
    assert r.status_code == 200
    assert r.json()["is_active"] == "archived"
    
    # Verify it's archived
    r = client.get(
        "/chat/conversations",
        params={"farmer_id": farmer_id, "status": "archived"}
    )
    
    data = r.json()
    assert len(data) == 1
    assert data[0]["is_active"] == "archived"
    
    print(f"✓ Conversation archived | ID: {conversation_id}")


def test_conversation_summary():
    """Test getting conversation summary."""
    print("\n[Test] Get conversation summary...")
    
    farmer_id, conversation_id = test_create_conversation()
    
    # Send some messages
    for i in range(2):
        payload = {"content": f"Message {i+1}", "message_type": "text"}
        client.post(
            f"/chat/conversations/{conversation_id}/messages",
            json=payload,
            params={"farmer_id": farmer_id}
        )
    
    # Get summary
    r = client.get(f"/chat/conversations/{conversation_id}/summary")
    
    assert r.status_code == 200
    data = r.json()
    
    assert data["message_count"] == 2
    assert data["conversation_id"] == conversation_id
    
    print(f"✓ Conversation summary retrieved | Messages: {data['message_count']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  CHAT INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_create_conversation()
        print()
        test_send_message()
        print()
        test_get_conversation_messages()
        print()
        test_list_farmer_conversations()
        print()
        test_mark_message_as_read()
        print()
        test_unread_count()
        print()
        test_archive_conversation()
        print()
        test_conversation_summary()
        
        print("\n" + "=" * 60)
        print("  ✓ ALL TESTS PASSED")
        print("=" * 60 + "\n")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
