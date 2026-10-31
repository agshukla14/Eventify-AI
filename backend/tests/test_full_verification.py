import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import EventIntake
from backend.app.plan_service import PlanService
from backend.app.database import SessionLocal

TEST_HOST = "127.0.0.1"
TEST_PORT = 8890


@pytest.fixture(scope="session", autouse=True)
def run_verification_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_14_point_full_verification():
    client = TestClient(app)

    # Check 4: Verify /api/health returns success
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
    assert health_res.json()["database"] == "connected"

    # Check 5: Verify events can be retrieved
    events_res = client.get("/api/events")
    assert events_res.status_code == 200
    events_list = events_res.json()
    assert isinstance(events_list, list)

    # Check 6 & 8 & 9 & 10: Create a new Birthday event and verify budget, timeline, vendors
    bday_payload = {
        "event_type": "birthday",
        "title": "Aarush 5th Birthday Blast",
        "date": "2027-04-15",
        "city": "Bengaluru",
        "guest_count": 50,
        "total_budget": 80000.0,
        "currency": "INR",
        "theme_style": "Super Mario Adventure",
        "cultural_preferences": "Fun kid celebration",
        "dietary_preferences": ["Vegetarian"],
        "must_haves": ["Themed Cake", "Magician Show"],
        "age_group_details": "Kids 4-6 years old",
    }
    bday_res = client.post("/api/events", json=bday_payload)
    assert bday_res.status_code == 200
    bday_plan = bday_res.json()
    bday_id = bday_plan["event_id"]

    # Test budget generation
    assert round(sum(i["percentage"] for i in bday_plan["budget"]["items"]), 2) == 100.00
    assert round(sum(i["allocated_amount"] for i in bday_plan["budget"]["items"]), 2) == 80000.0
    assert any(i["is_contingency"] for i in bday_plan["budget"]["items"])

    # Test timeline generation
    assert len(bday_plan["timeline"]["milestones"]) >= 4
    assert len(bday_plan["timeline"]["run_of_show"]) >= 4

    # Test vendor management
    assert len(bday_plan["vendors"]) >= 4
    for v in bday_plan["vendors"]:
        assert len(v["checklist"]) >= 4

    # Check 7: Create a wedding event
    wedding_payload = {
        "event_type": "wedding",
        "title": "Karan & Simran Royal Wedding",
        "date": "2027-09-20",
        "city": "Udaipur",
        "guest_count": 400,
        "total_budget": 3000000.0,
        "currency": "INR",
        "theme_style": "Lakeside Royal Palace",
        "cultural_preferences": "Punjabi & Marwari Fusion",
        "dietary_preferences": ["Vegetarian", "Jain Options"],
        "must_haves": ["Baraat Procession", "Live Sufi Music"],
    }
    wed_res = client.post("/api/events", json=wedding_payload)
    assert wed_res.status_code == 200
    wed_plan = wed_res.json()
    wed_id = wed_plan["event_id"]
    assert round(sum(i["percentage"] for i in wed_plan["budget"]["items"]), 2) == 100.00
    assert round(sum(i["allocated_amount"] for i in wed_plan["budget"]["items"]), 2) == 3000000.0

    # Check 11: Test AI assistant chat grounded Q&A and tool modification
    chat_res = client.post(
        "/api/chat",
        json={"event_id": bday_id, "message": "How many days left until my event?"}
    )
    assert chat_res.status_code == 200
    assert "days remaining" in chat_res.json()["reply"] or "days left" in chat_res.json()["reply"].lower()

    # Tool call: Move budget
    chat_tool_res = client.post(
        "/api/chat",
        json={"event_id": bday_id, "message": "move 4000 from Decor to Catering"}
    )
    assert chat_tool_res.status_code == 200
    updated_plan = chat_tool_res.json()["updated_plan"]
    assert updated_plan is not None
    assert round(sum(i["percentage"] for i in updated_plan["budget"]["items"]), 2) == 100.00

    # Check 12: Test PDF and CSV exports
    csv_res = client.get(f"/api/events/{bday_id}/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "BUDGET ALLOCATION" in csv_res.text

    pdf_res = client.get(f"/api/events/{bday_id}/export/pdf")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    assert len(pdf_res.content) > 1000

    # Check 1, 2, 3, 14: Playwright browser check for loading, dashboard & console errors
    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        # Load root website
        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("header", timeout=5000)
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        # Verify dashboard loaded with cards
        assert page.locator("text=Days Remaining").first.is_visible()
        assert page.locator("text=Budget Utilized").first.is_visible()
        assert page.locator("text=Tasks Completed").first.is_visible()
        assert page.locator("text=Vendors Booked").first.is_visible()

        browser.close()

    assert len(console_errors) == 0, f"Frontend console errors found: {console_errors}"
    assert len(page_errors) == 0, f"Frontend page errors found: {page_errors}"

    # Clean up test events
    client.delete(f"/api/events/{bday_id}")
    client.delete(f"/api/events/{wed_id}")
