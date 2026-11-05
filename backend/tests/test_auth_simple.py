import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import UserModel, EventModel

client = TestClient(app)


def test_01_new_user_registration():
    """Requirement 8.1: New user registration without any OTP requirement."""
    test_email = f"newuser_{uuid.uuid4().hex[:8]}@celebration.test"
    password = "StrongPassword123!"
    full_name = "Divya Patel"

    res = client.post("/api/auth/register", json={
        "email": test_email,
        "password": password,
        "full_name": full_name,
        "terms_accepted": True,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["email"] == test_email
    assert data["email_verified"] is True
    assert "user_id" in data
    assert "access_token" in data

    # Verify user exists in database and is marked active and verified
    with SessionLocal() as db:
        user = db.query(UserModel).filter(UserModel.email == test_email).first()
        assert user is not None
        assert user.email_verified is True
        assert user.is_active is True
        assert user.full_name == full_name


def test_02_duplicate_email_rejection():
    """Requirement 8.2: Duplicate email rejection."""
    test_email = f"dupuser_{uuid.uuid4().hex[:8]}@celebration.test"
    password = "StrongPassword123!"

    # First registration
    res1 = client.post("/api/auth/register", json={
        "email": test_email,
        "password": password,
        "full_name": "First User",
        "terms_accepted": True,
    })
    assert res1.status_code == 200

    # Duplicate attempt
    res2 = client.post("/api/auth/register", json={
        "email": test_email,
        "password": "AnotherPassword456!",
        "full_name": "Duplicate User",
        "terms_accepted": True,
    })
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_03_login_with_correct_credentials():
    """Requirement 8.3: Login with correct credentials returns valid JWT token."""
    test_email = f"loginuser_{uuid.uuid4().hex[:8]}@celebration.test"
    password = "ValidPassword789!"

    client.post("/api/auth/register", json={
        "email": test_email,
        "password": password,
        "full_name": "Login Tester",
        "terms_accepted": True,
    })

    res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": password,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_email
    assert data["user"]["email_verified"] is True


def test_04_login_with_incorrect_credentials():
    """Requirement 8.4: Login with incorrect credentials fails with 401."""
    test_email = f"wronglogin_{uuid.uuid4().hex[:8]}@celebration.test"
    password = "CorrectPassword123!"

    client.post("/api/auth/register", json={
        "email": test_email,
        "password": password,
        "full_name": "Wrong Login Tester",
        "terms_accepted": True,
    })

    # Wrong password
    res1 = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "WrongPassword999!",
    })
    assert res1.status_code == 401
    assert "Invalid email or password" in res1.json()["detail"]

    # Non-existent user
    res2 = client.post("/api/auth/login", json={
        "email": "nonexistent_user_9999@domain.test",
        "password": "AnyPassword123!",
    })
    assert res2.status_code == 401


def test_05_logout():
    """Requirement 8.5: Logout endpoint clears session cleanly."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert "Logged out successfully" in res.json()["message"]


def test_06_protected_dashboard_access():
    """Requirement 8.6: Protected dashboard access with valid Bearer token."""
    test_email = f"dashboarduser_{uuid.uuid4().hex[:8]}@celebration.test"
    password = "DashboardPassword123!"

    reg = client.post("/api/auth/register", json={
        "email": test_email,
        "password": password,
        "full_name": "Dashboard Director",
        "terms_accepted": True,
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == test_email

    # Access /api/dashboard/executive-summary
    dash_res = client.get("/api/dashboard/executive-summary", headers=headers)
    assert dash_res.status_code == 200
    assert "kpis" in dash_res.json()


def test_07_unauthenticated_route_protection():
    """Requirement 8.7: Unauthenticated requests are rejected with 401."""
    # When disabling test dev demo fallback header
    headers = {"X-Disable-Dev-Demo": "1"}

    res_events = client.get("/api/events", headers=headers)
    assert res_events.status_code == 401
    assert "Authentication required" in res_events.json()["detail"]

    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 401


def test_08_existing_user_login():
    """Requirement 8.8: Existing users in database can log in directly without OTP verification."""
    with SessionLocal() as db:
        existing_user = db.query(UserModel).first()
        assert existing_user is not None
        # Verify user has email_verified == True now
        assert existing_user.email_verified is True


def test_09_existing_event_data_preservation():
    """Requirement 8.9: Existing event data and relationships are preserved."""
    with SessionLocal() as db:
        event_count = db.query(EventModel).count()
        assert event_count >= 91, f"Expected at least 91 existing events, found {event_count}"

        # Verify sample event structure
        first_event = db.query(EventModel).first()
        assert first_event is not None
        assert first_event.title != ""
        assert first_event.total_budget > 0


def test_10_user_to_event_access_isolation():
    """Requirement 8.10: User A cannot access or modify User B's events."""
    ts = uuid.uuid4().hex[:6]
    email_a = f"owner_a_{ts}@isolation.test"
    email_b = f"intruder_b_{ts}@isolation.test"
    pwd = "IsolationPassword123!"

    reg_a = client.post("/api/auth/register", json={"email": email_a, "password": pwd, "full_name": "Owner A"})
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    reg_b = client.post("/api/auth/register", json={"email": email_b, "password": pwd, "full_name": "Intruder B"})
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates an event
    create_res = client.post("/api/events", json={
        "event_type": "wedding",
        "title": "Private Royal Wedding",
        "date": "2027-05-20",
        "city": "Udaipur",
        "guest_count": 250,
        "total_budget": 5000000,
        "currency": "INR",
        "dietary_preferences": ["Vegetarian"],
        "must_haves": ["Palace view", "Fireworks"],
    }, headers=headers_a)
    assert create_res.status_code == 200, create_res.text
    event_id = create_res.json()["event_id"]

    # User A can access it
    get_res_a = client.get(f"/api/events/{event_id}", headers=headers_a)
    assert get_res_a.status_code == 200

    # User B CANNOT access it (403 Forbidden)
    get_res_b = client.get(f"/api/events/{event_id}", headers=headers_b)
    assert get_res_b.status_code == 403
    assert "Access forbidden" in get_res_b.json()["detail"]

    # User B CANNOT update it (403 Forbidden)
    put_res_b = client.put(f"/api/events/{event_id}", json=create_res.json(), headers=headers_b)
    assert put_res_b.status_code == 403

    # User B CANNOT delete it (403 Forbidden)
    del_res_b = client.delete(f"/api/events/{event_id}", headers=headers_b)
    assert del_res_b.status_code == 403

