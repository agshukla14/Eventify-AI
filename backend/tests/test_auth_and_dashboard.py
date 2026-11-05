import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_auth_registration_and_login_flow():
    test_email = f"planner_{uuid.uuid4().hex[:8]}@celebration.test"
    test_password = "SecurePassword987!"
    test_name = "Aarav Sharma"

    # 1. Register new user
    reg_res = client.post(
        "/api/auth/register",
        json={"email": test_email, "password": test_password, "full_name": test_name},
    )
    assert reg_res.status_code == 200, reg_res.text
    reg_data = reg_res.json()
    assert reg_data["email"] == test_email
    assert reg_data["email_verified"] is True

    # 2. Prevent duplicate email registration
    dup_res = client.post(
        "/api/auth/register",
        json={"email": test_email, "password": "AnotherPassword123!", "full_name": "Duplicate Test"},
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 3. Invalid login rejection
    bad_login = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 4. Successful login
    login_res = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    assert login_data["user"]["id"] == reg_data["user_id"]

    # 5. Profile check with Bearer token
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == test_email
    assert me_data["full_name"] == test_name


def test_unauthenticated_demo_fallback():
    # If no Bearer token is provided, /api/auth/me returns the demo organizer gracefully
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert "demo" in me_data["email"]
    assert me_data["is_active"] is True


def test_executive_dashboard_summary_kpis():
    # Call executive summary endpoint
    res = client.get("/api/dashboard/executive-summary")
    assert res.status_code == 200, res.text
    data = res.json()

    # 1. Verify 8 KPI metrics exist and are well-typed
    kpis = data["kpis"]
    assert "total_events" in kpis
    assert "upcoming_events" in kpis
    assert "total_planned_budget" in kpis
    assert "total_actual_expenses" in kpis
    assert "remaining_budget" in kpis
    assert "total_confirmed_guests" in kpis
    assert "pending_rsvps" in kpis
    assert "booked_vendors" in kpis

    assert isinstance(kpis["total_events"], int)
    assert isinstance(kpis["upcoming_events"], int)
    assert isinstance(kpis["total_planned_budget"], (int, float))
    assert isinstance(kpis["total_actual_expenses"], (int, float))
    assert isinstance(kpis["remaining_budget"], (int, float))
    assert isinstance(kpis["total_confirmed_guests"], int)
    assert isinstance(kpis["pending_rsvps"], int)
    assert isinstance(kpis["booked_vendors"], int)

    # 2. Verify upcoming events list
    assert "upcoming_events" in data
    assert isinstance(data["upcoming_events"], list)
    if len(data["upcoming_events"]) > 0:
        ev0 = data["upcoming_events"][0]
        assert "event_id" in ev0
        assert "title" in ev0
        assert "days_left" in ev0
        assert "total_budget" in ev0
        assert "actual_spent" in ev0

    # 3. Verify recent activities feed
    assert "recent_activities" in data
    assert isinstance(data["recent_activities"], list)

    # 4. Verify budget utilization categories
    assert "budget_utilization" in data
    assert isinstance(data["budget_utilization"], list)

    # 5. Verify guest RSVP breakdown
    assert "guest_rsvp_breakdown" in data
    gr = data["guest_rsvp_breakdown"]
    assert "confirmed" in gr
    assert "declined" in gr
    assert "pending" in gr
    assert "total_invited" in gr
    assert "total_attending" in gr

    # 6. Verify vendor summary
    assert "vendor_summary" in data
    vs = data["vendor_summary"]
    assert "booked_count" in vs
    assert "shortlisted_count" in vs
    assert "total_contracted_amount" in vs
    assert "advance_paid_amount" in vs

    # 7. Verify weather alert widget
    assert "next_event_weather_alert" in data
    if data["next_event_weather_alert"]:
        wa = data["next_event_weather_alert"]
        assert "overall_risk_level" in wa
        assert "primary_concern" in wa
        assert "recommended_action" in wa
