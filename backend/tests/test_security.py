import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth_service import get_jwt_secret, create_access_token, _DEV_FALLBACK_SECRET

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_users():
    """Sets up two isolated users (User A and User B) for IDOR and authorization testing."""
    ts = int(datetime.now().timestamp() * 1000)
    user_a_email = f"user_a_{ts}@eventify.test"
    user_b_email = f"user_b_{ts}@eventify.test"
    password = "SecurePassword123!"

    res_a = client.post("/api/auth/register", json={
        "email": user_a_email,
        "password": password,
        "full_name": "User Alpha"
    })
    assert res_a.status_code == 200, res_a.text
    user_a_id = res_a.json()["user_id"]
    login_a = client.post("/api/auth/login", json={"email": user_a_email, "password": password})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]

    res_b = client.post("/api/auth/register", json={
        "email": user_b_email,
        "password": password,
        "full_name": "User Beta"
    })
    assert res_b.status_code == 200, res_b.text
    user_b_id = res_b.json()["user_id"]
    login_b = client.post("/api/auth/login", json={"email": user_b_email, "password": password})
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]

    return {
        "user_a": {"id": user_a_id, "token": token_a, "headers": {"Authorization": f"Bearer {token_a}"}},
        "user_b": {"id": user_b_id, "token": token_b, "headers": {"Authorization": f"Bearer {token_b}"}},
    }


@pytest.fixture(scope="module")
def user_b_resources(auth_users):
    """Creates a sample event and child entities owned strictly by User B."""
    headers_b = auth_users["user_b"]["headers"]

    # 1. User B creates an event
    event_payload = {
        "event_type": "wedding",
        "title": "Beta's Royal Wedding",
        "date": "2026-11-20",
        "city": "Udaipur",
        "total_budget": 500000.0,
        "guest_count": 150
    }
    res_event = client.post("/api/events", json=event_payload, headers=headers_b)
    assert res_event.status_code == 200, res_event.text
    event_data = res_event.json()
    event_id = event_data["event_id"]

    # 2. User B creates an expense
    expense_payload = {
        "expense_name": "Beta Floral Design",
        "category": "Decor",
        "amount": 45000.0,
        "expense_date": "2026-11-10",
        "payment_status": "Paid",
        "vendor_name": "Royal Florals",
        "notes": "User B expense notes"
    }
    res_exp = client.post(f"/api/events/{event_id}/expenses", json=expense_payload, headers=headers_b)
    assert res_exp.status_code == 200, res_exp.text
    expense_id = res_exp.json()["id"]

    # 3. User B creates a guest
    guest_payload = {
        "full_name": "Beta VIP Guest",
        "category": "VIP",
        "email": "vip_guest_b@test.com",
        "phone": "+919876543210",
        "rsvp_status": "Accepted",
        "plus_ones": 1
    }
    res_gst = client.post(f"/api/events/{event_id}/guests", json=guest_payload, headers=headers_b)
    assert res_gst.status_code == 200, res_gst.text
    guest_id = res_gst.json()["id"]

    # 4. User B creates an invitation
    inv_payload = {
        "event_id": event_id,
        "title": "Beta Royal Invitation Card",
        "language": "English",
        "text_components": {
            "personalized_greeting": "Dear Friends and Family",
            "event_details": "November 20, 2026 at 7 PM at Lake Palace, Udaipur",
            "invitation_message": "We cordially invite you to celebrate the royal wedding of Beta.",
            "closing_message": "Warm regards, The Beta Family",
            "full_text": "Dear Friends and Family, We cordially invite you to celebrate the royal wedding of Beta. November 20, 2026 at 7 PM at Lake Palace, Udaipur. Warm regards, The Beta Family"
        },
        "design_config": {
            "template_id": "royal_gold",
            "primary_color": "#D4AF37",
            "font_family": "serif"
        }
    }
    res_inv = client.post(f"/api/events/{event_id}/invitations", json=inv_payload, headers=headers_b)
    assert res_inv.status_code == 200, res_inv.text
    invitation_id = res_inv.json()["id"]

    # 5. User B books a vendor
    vendors_res = client.get("/api/vendors")
    assert vendors_res.status_code == 200 and len(vendors_res.json()) > 0
    vendor_id = vendors_res.json()[0]["id"]

    booking_payload = {
        "event_id": event_id,
        "vendor_id": vendor_id,
        "agreed_price": 60000.0,
        "advance_payment": 20000.0,
        "booking_status": "Booked"
    }
    res_bkg = client.post(f"/api/events/{event_id}/vendor-bookings", json=booking_payload, headers=headers_b)
    assert res_bkg.status_code == 200, res_bkg.text
    booking_id = res_bkg.json()["id"]

    return {
        "event_id": event_id,
        "expense_id": expense_id,
        "guest_id": guest_id,
        "invitation_id": invitation_id,
        "booking_id": booking_id,
    }


# ============================================================================
# Security Test Scenarios 1-12
# ============================================================================

def test_01_unauthenticated_requests_to_private_endpoints(user_b_resources):
    """
    Scenario 1: Unauthenticated requests to private endpoints must be rejected with 401
    when dev-demo bypass is disabled or in production.
    """
    event_id = user_b_resources["event_id"]
    headers = {"X-Disable-Dev-Demo": "true"}

    endpoints = [
        ("GET", "/api/events"),
        ("GET", f"/api/events/{event_id}"),
        ("GET", f"/api/events/{event_id}/expenses"),
        ("GET", f"/api/events/{event_id}/guests"),
        ("GET", f"/api/events/{event_id}/invitations"),
        ("GET", f"/api/events/{event_id}/vendor-bookings"),
        ("GET", f"/api/events/{event_id}/weather"),
    ]

    for method, path in endpoints:
        res = client.request(method, path, headers=headers)
        assert res.status_code == 401, f"Expected 401 on unauthenticated {method} {path}, got {res.status_code}"


def test_02_user_a_cannot_access_user_b_event(auth_users, user_b_resources):
    """
    Scenario 2: User A attempting to access User B's event must receive 403 Forbidden (IDOR protection).
    """
    headers_a = auth_users["user_a"]["headers"]
    event_id_b = user_b_resources["event_id"]

    res = client.get(f"/api/events/{event_id_b}", headers=headers_a)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert "forbidden" in res.json()["detail"].lower()


def test_03_user_a_cannot_update_user_b_event(auth_users, user_b_resources):
    """
    Scenario 3: User A attempting to update User B's event must receive 403 Forbidden.
    """
    headers_a = auth_users["user_a"]["headers"]
    headers_b = auth_users["user_b"]["headers"]
    event_id_b = user_b_resources["event_id"]

    res_b_event = client.get(f"/api/events/{event_id_b}", headers=headers_b)
    assert res_b_event.status_code == 200, res_b_event.text
    update_payload = res_b_event.json()
    update_payload["intake"]["title"] = "Hacked Wedding Title"

    res = client.put(f"/api/events/{event_id_b}", json=update_payload, headers=headers_a)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"


def test_04_user_a_cannot_delete_user_b_event(auth_users, user_b_resources):
    """
    Scenario 4: User A attempting to delete User B's event must receive 403 Forbidden.
    """
    headers_a = auth_users["user_a"]["headers"]
    event_id_b = user_b_resources["event_id"]

    res = client.delete(f"/api/events/{event_id_b}", headers=headers_a)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"


def test_05_cross_user_access_to_expenses(auth_users, user_b_resources):
    """
    Scenario 5: User A attempting to list, create, view, or delete User B's expenses
    must receive 403 Forbidden.
    """
    headers_a = auth_users["user_a"]["headers"]
    event_id_b = user_b_resources["event_id"]
    expense_id_b = user_b_resources["expense_id"]

    # 1. List expenses
    res_list = client.get(f"/api/events/{event_id_b}/expenses", headers=headers_a)
    assert res_list.status_code == 403, res_list.text

    # 2. Add expense to User B's event
    res_create = client.post(
        f"/api/events/{event_id_b}/expenses",
        json={
            "expense_name": "Attacker Expense",
            "category": "Decor",
            "amount": 999.0,
            "expense_date": "2026-11-10",
            "payment_status": "Pending",
        },
        headers=headers_a,
    )
    assert res_create.status_code == 403, res_create.text

    # 3. View single expense
    res_get = client.get(f"/api/events/{event_id_b}/expenses/{expense_id_b}", headers=headers_a)
    assert res_get.status_code == 403, res_get.text

    # 4. Delete expense
    res_del = client.delete(f"/api/events/{event_id_b}/expenses/{expense_id_b}", headers=headers_a)
    assert res_del.status_code == 403, res_del.text


def test_06_cross_user_access_to_guests(auth_users, user_b_resources):
    """
    Scenario 6: User A attempting to access User B's guest list or guest records
    must receive 403 Forbidden.
    """
    headers_a = auth_users["user_a"]["headers"]
    event_id_b = user_b_resources["event_id"]
    guest_id_b = user_b_resources["guest_id"]

    # 1. List guests
    res_list = client.get(f"/api/events/{event_id_b}/guests", headers=headers_a)
    assert res_list.status_code == 403, res_list.text

    # 2. Add guest
    res_create = client.post(
        f"/api/events/{event_id_b}/guests",
        json={"full_name": "Attacker Guest", "category": "Friends"},
        headers=headers_a,
    )
    assert res_create.status_code == 403, res_create.text

    # 3. View single guest
    res_get = client.get(f"/api/events/{event_id_b}/guests/{guest_id_b}", headers=headers_a)
    assert res_get.status_code == 403, res_get.text

    # 4. Delete guest
    res_del = client.delete(f"/api/events/{event_id_b}/guests/{guest_id_b}", headers=headers_a)
    assert res_del.status_code == 403, res_del.text


def test_07_cross_user_access_to_invitations(auth_users, user_b_resources):
    """
    Scenario 7: User A attempting to view, create, or delete User B's invitations
    must receive 403 Forbidden.
    """
    headers_a = auth_users["user_a"]["headers"]
    event_id_b = user_b_resources["event_id"]
    invitation_id_b = user_b_resources["invitation_id"]

    # 1. List invitations of event B
    res_list = client.get(f"/api/events/{event_id_b}/invitations", headers=headers_a)
    assert res_list.status_code == 403, res_list.text

    # 2. View specific invitation directly by ID
    res_get = client.get(f"/api/invitations/{invitation_id_b}", headers=headers_a)
    assert res_get.status_code == 403, res_get.text

    # 3. Delete specific invitation
    res_del = client.delete(f"/api/invitations/{invitation_id_b}", headers=headers_a)
    assert res_del.status_code == 403, res_del.text


def test_08_cross_user_access_to_vendor_bookings(auth_users, user_b_resources):
    """
    Scenario 8: User A attempting to access User B's vendor bookings
    must receive 403 Forbidden.
    """
    headers_a = auth_users["user_a"]["headers"]
    event_id_b = user_b_resources["event_id"]
    booking_id_b = user_b_resources["booking_id"]

    # 1. List bookings
    res_list = client.get(f"/api/events/{event_id_b}/vendor-bookings", headers=headers_a)
    assert res_list.status_code == 403, res_list.text

    # 2. Update booking
    res_upd = client.put(
        f"/api/vendor-bookings/{booking_id_b}",
        json={"booking_status": "Cancelled"},
        headers=headers_a,
    )
    assert res_upd.status_code == 403, res_upd.text

    # 3. Delete booking
    res_del = client.delete(f"/api/vendor-bookings/{booking_id_b}", headers=headers_a)
    assert res_del.status_code == 403, res_del.text


def test_09_invalid_jwt_tokens():
    """
    Scenario 9: Tampered, corrupted, or forged JWT tokens must be rejected with 401 Unauthorized.
    """
    invalid_tokens = [
        "Bearer totally.invalid.token",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsignature",
        "Bearer malformed_token_string",
    ]
    for token in invalid_tokens:
        res = client.get("/api/events", headers={"Authorization": token})
        assert res.status_code == 401, f"Expected 401 for token '{token}', got {res.status_code}"


def test_10_expired_jwt_tokens(auth_users):
    """
    Scenario 10: Tokens with an expired 'exp' timestamp must be rejected with 401 Unauthorized.
    """
    user_id = auth_users["user_a"]["id"]
    # Generate token that expired 1 hour ago
    expired_token = create_access_token({"sub": user_id, "email": "expired@eventify.test"}, expires_delta=-3600)

    res = client.get("/api/events", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401, f"Expected 401 for expired token, got {res.status_code}"
    assert "expired" in res.json()["detail"].lower()


def test_11_missing_production_secret(monkeypatch):
    """
    Scenario 11: In production mode (APP_ENV=production), if JWT_SECRET is unset or empty,
    the application must immediately fail safely with RuntimeError rather than running insecurely.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        get_jwt_secret()

    assert "CRITICAL SECURITY ERROR: JWT_SECRET environment variable is required in production mode." in str(exc_info.value)


def test_12_disallowed_cors_origins():
    """
    Scenario 12: Requests from unauthorized external origins must not receive
    permissive CORS headers or wildcard access when credentials are in use.
    """
    attacker_origin = "https://malicious-event-stealer.xyz"

    res = client.options(
        "/api/events",
        headers={
            "Origin": attacker_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    # The Access-Control-Allow-Origin header must either be absent or NOT equal to attacker's origin
    allowed_origin = res.headers.get("access-control-allow-origin")
    assert allowed_origin != attacker_origin, f"Disallowed origin was incorrectly permitted: {allowed_origin}"


def test_13_production_mode_auth_enforcement_and_bearer_token(monkeypatch, auth_users):
    """
    Scenario 13: In production mode (APP_ENV=production):
    - GET /api/events without credentials MUST return 401 'Authentication required. Please sign in to access this resource.'
    - GET /api/events WITH Bearer token MUST succeed with 200.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", _DEV_FALLBACK_SECRET)

    # 1. Without credentials -> 401
    res_no_auth = client.get("/api/events")
    assert res_no_auth.status_code == 401
    assert res_no_auth.json()["detail"] == "Authentication required. Please sign in to access this resource."

    # 2. With valid Bearer token -> 200
    headers_a = auth_users["user_a"]["headers"]
    res_auth = client.get("/api/events", headers=headers_a)
    assert res_auth.status_code == 200
    assert isinstance(res_auth.json(), list)


def test_14_export_downloads_with_query_param_token(monkeypatch, auth_users, user_b_resources):
    """
    Scenario 14: File export downloads in production mode (APP_ENV=production):
    - Normal browser navigation to export URLs without headers but with ?token=<jwt> must succeed.
    - Missing token in production mode must return 401.
    - Invalid token in ?token=<jwt> must return 401.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", _DEV_FALLBACK_SECRET)
    event_id = user_b_resources["event_id"]
    token_b = auth_users["user_b"]["token"]

    # 1. Export with valid query param token -> 200
    csv_res = client.get(f"/api/events/{event_id}/export/csv?token={token_b}")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")

    pdf_res = client.get(f"/api/events/{event_id}/export/pdf?token={token_b}")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers.get("content-type", "")

    # 2. Export without token in production -> 401
    unauth_res = client.get(f"/api/events/{event_id}/export/csv")
    assert unauth_res.status_code == 401
    assert unauth_res.json()["detail"] == "Authentication required. Please sign in to access this resource."

    # 3. Export with invalid token -> 401
    bad_token_res = client.get(f"/api/events/{event_id}/export/csv?token=invalid.jwt.token")
    assert bad_token_res.status_code == 401
    assert "invalid or expired" in bad_token_res.json()["detail"].lower()

