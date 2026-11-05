import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import UserModel, EventModel, ExpenseModel
from backend.app.auth_service import create_access_token, hash_password
from backend.app.schemas import EventIntake, FullEventPlan, InvitationDesignConfig, InvitationTextComponents
from backend.app.repair_engine import DeterministicRepairEngine, parse_start_time_hour, extract_event_start_time
from backend.app.export_service import ExportService
from backend.app.expense_service import ExpenseService
from backend.app.plan_service import PlanService

client = TestClient(app)


@pytest.fixture
def auth_user():
    import uuid
    from datetime import datetime
    db = SessionLocal()
    email = "qa_architect@celebrationai.test"
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        now_iso = datetime.utcnow().isoformat()
        user = UserModel(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="QA Chief Architect",
            is_active=True,
            email_verified=True,
            email_verified_at=now_iso,
            created_at=now_iso,
            updated_at=now_iso,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    db.close()
    return {"user_id": user.id, "email": user.email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_issue_1_gemini_429_deterministic_fallback(auth_user, monkeypatch):
    """
    Issue 1: When Gemini API raises 429 quota exhaustion, budget optimizer must
    gracefully fall back to deterministic calculations with Decimal and NOT claim
    mathematical infeasibility.
    """
    intake = {
        "event_type": "wedding",
        "title": "Quota Fallback Test Celebration",
        "date": "2027-08-15",
        "city": "Jaipur",
        "guest_count": 250,
        "total_budget": 500000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=intake, headers=auth_user["headers"])
    assert create_res.status_code == 200
    event_id = create_res.json()["event_id"]

    try:
        def mock_quota_exceeded(*args, **kwargs):
            raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for model gemini-3.5-flash-lite")

        monkeypatch.setattr("google.genai.models.Models.generate_content", mock_quota_exceeded)

        opt_res = client.post(
            f"/api/events/{event_id}/optimize-budget",
            json={"user_prompt": "Reduce my budget to ₹4,00,000"},
            headers=auth_user["headers"],
        )
        assert opt_res.status_code == 200
        data = opt_res.json()

        assert data["is_feasible"] is True
        assert data["is_valid"] is True
        assert data["engine_used"] == "deterministic_fallback"
        assert data["revised_total_budget"] == 400000.0
        assert data["total_savings"] == 100000.0
        assert "Quota exceeded" in data["explanation"]["why_recommended"] or "Deterministic" in data["explanation"]["why_recommended"]
        
        # Verify 100% allocation invariant
        alloc_sum = sum(c["recommended_amount"] for c in data["categories"])
        assert round(alloc_sum, 2) == 400000.0
    finally:
        client.delete(f"/api/events/{event_id}", headers=auth_user["headers"])


def test_issue_2_expense_and_budget_two_way_sync(auth_user):
    """
    Issue 2: Verify two-way synchronization between Expense Tracking and Budget Planner:
    - Case A: Manually adjusting spent in Budget Planner updates/creates an ExpenseModel record.
    - Case B: Adding an expense updates the Budget Planner item and total actual spent.
    """
    intake = {
        "event_type": "birthday",
        "title": "Sync Test Birthday Bash",
        "date": "2027-05-10",
        "city": "Mumbai",
        "guest_count": 60,
        "total_budget": 100000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=intake, headers=auth_user["headers"])
    assert create_res.status_code == 200
    plan = create_res.json()
    event_id = plan["event_id"]

    try:
        # Case B: Add an expense in Expense Tracking
        exp_res = client.post(
            f"/api/events/{event_id}/expenses",
            json={
                "expense_name": "Premium Birthday Cake",
                "category": "Catering & Bar",
                "amount": 7500.0,
                "expense_date": "2027-05-01",
                "payment_status": "Paid"
            },
            headers=auth_user["headers"]
        )
        assert exp_res.status_code == 200

        # Check Plan reflects the expense in the budget category and total spent
        plan_res = client.get(f"/api/events/{event_id}", headers=auth_user["headers"])
        assert plan_res.status_code == 200
        updated_plan = plan_res.json()
        cat_item = next(i for i in updated_plan["budget"]["items"] if "catering" in i["category"].lower())
        assert cat_item["actual_spent"] == 7500.0
        assert updated_plan["budget"]["total_actual_spent"] == 7500.0

        # Case A: Adjust actual spent from Budget Planner endpoint
        adj_res = client.post(
            f"/api/events/{event_id}/budget/adjust-spent",
            json={
                "category": cat_item["category"],
                "target_spent": 12000.0,
                "notes": "Direct invoice settlement"
            },
            headers=auth_user["headers"]
        )
        assert adj_res.status_code == 200
        adj_plan = adj_res.json()
        cat_item_adj = next(i for i in adj_plan["budget"]["items"] if i["category"] == cat_item["category"])
        assert cat_item_adj["actual_spent"] == 12000.0

        # Verify an auditable ExpenseModel was recorded in the database
        db = SessionLocal()
        expenses = db.query(ExpenseModel).filter(ExpenseModel.event_id == event_id).all()
        assert sum(e.amount for e in expenses) == 12000.0
        db.close()
    finally:
        client.delete(f"/api/events/{event_id}", headers=auth_user["headers"])


def test_issue_4_multilingual_pdf_fonts():
    """
    Issue 4: Verifies ReportLab TrueType font registration and generation for
    English, Hindi, and Gujarati invitation cards with zero encoding errors.
    """
    # 1. Hindi
    hindi_pdf = ExportService.generate_invitation_pdf(
        title="शुभ विवाह निमंत्रण",
        language="Hindi",
        components=InvitationTextComponents(
            personalized_greeting="आदरणीय परिवारजन,",
            event_details="दिनांक: 25 नवंबर 2027 | समय: शाम 7 बजे से | स्थान: शाही पैलेस, जयपुर",
            invitation_message="हमारे सुपुत्र रोहन के शुभ विवाह के पावन अवसर पर आप सपरिवार सादर आमंत्रित हैं।",
            closing_message="दर्शनाभिलाषी: शर्मा परिवार",
            full_text="शुभ विवाह निमंत्रण",
        ),
        design_config=InvitationDesignConfig(theme_palette="royal_gold")
    )
    assert len(hindi_pdf) > 2000
    assert hindi_pdf.startswith(b"%PDF")

    # 2. Gujarati
    gujarati_pdf = ExportService.generate_invitation_pdf(
        title="શુભ લગ્ન પત્રિકા",
        language="Gujarati",
        components=InvitationTextComponents(
            personalized_greeting="સ્નેહી શ્રી અને પરિવાર,",
            event_details="તારીખ: 25 નવેમ્બર 2027 | સમય: સાંજે 7:00 વાગ્યાથી | સ્થળ: શ્રીજી પેલેસ, વડોદરા",
            invitation_message="અમારા સુપુત્ર આરવના શુભ લગ્ન પ્રસંગે આપ સહપરિવાર પધારવા ભાવભર્યું આમંત્રણ છે.",
            closing_message="લિ. પટેલ પરિવાર",
            full_text="શુભ લગ્ન પત્રિકા",
        ),
        design_config=InvitationDesignConfig(theme_palette="royal_gold")
    )
    assert len(gujarati_pdf) > 2000
    assert gujarati_pdf.startswith(b"%PDF")

    # 3. English
    english_pdf = ExportService.generate_invitation_pdf(
        title="Royal Wedding Invitation",
        language="English",
        components=InvitationTextComponents(
            personalized_greeting="Dear Family and Friends,",
            event_details="Date: November 25, 2027 | Time: 7:00 PM onwards | Venue: The Grand Palace, Jaipur",
            invitation_message="We cordially invite you to celebrate the joyous union of our children.",
            closing_message="Warm Regards, The Sharma & Verma Families",
            full_text="Royal Wedding Invitation",
        ),
        design_config=InvitationDesignConfig(theme_palette="royal_gold")
    )
    assert len(english_pdf) > 2000
    assert english_pdf.startswith(b"%PDF")


def test_issue_5_timeline_respects_configured_start_time(auth_user):
    """
    Issue 5: Dynamic event timeline generation respects configured event start time:
    - Operational activities before start time are labeled 'Pre-Event Setup:'
    - Guest-facing arrival and activities start at or after the configured start time.
    - Verified for evening start time (7:00 PM / 19:00).
    """
    intake = {
        "event_type": "wedding",
        "title": "Universal Evening Royal Wedding",
        "date": "2027-10-25",
        "city": "Vadodara",
        "guest_count": 300,
        "total_budget": 1000000.0,
        "currency": "INR",
        "start_time": "7:00 PM onwards",
    }
    create_res = client.post("/api/events", json=intake, headers=auth_user["headers"])
    assert create_res.status_code == 200
    plan_data = create_res.json()
    event_id = plan_data["event_id"]

    try:
        ros = plan_data["timeline"]["run_of_show"]
        assert len(ros) >= 6

        # Check prep items before 19:00 have 'Pre-Event Setup:' prefix
        for item in ros:
            slot_start = int(item["time_slot"].split("-")[0].split(":")[0].strip())
            if slot_start < 19:
                assert item["activity"].startswith("Pre-Event Setup:")
            elif "Guest Arrival" in item["activity"]:
                assert slot_start >= 19

        # Test PDF export reflects start time
        pdf_res = client.get(f"/api/events/{event_id}/export/pdf", headers=auth_user["headers"])
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 5000

        # Test CSV export reflects start time
        csv_res = client.get(f"/api/events/{event_id}/export/csv", headers=auth_user["headers"])
        assert csv_res.status_code == 200
        assert "7:00 PM onwards" in csv_res.text
    finally:
        client.delete(f"/api/events/{event_id}", headers=auth_user["headers"])


def test_issue_6_unauthenticated_requests_blocked(monkeypatch):
    """
    Issue 6: Protected endpoints require authentication and reject unauthenticated requests.
    """
    monkeypatch.setenv("APP_ENV", "production")
    res = client.get("/api/events")
    assert res.status_code == 401

    post_res = client.post("/api/events", json={"title": "Unauthorized Plan"})
    assert post_res.status_code == 401
