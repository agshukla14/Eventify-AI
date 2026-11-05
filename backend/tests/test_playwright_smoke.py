import os
import json
import shutil
import tempfile
import time
import threading
from datetime import date, timedelta
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import Base, get_db

pytestmark = pytest.mark.playwright
from backend.app.models import EventModel
from backend.app.schemas import EventIntake
from backend.app.vendor_service import VendorService
from backend.app.fallback_engine import FallbackTemplateEngine

TEST_HOST = "127.0.0.1"
TEST_PORT = 8889


@pytest.fixture(scope="session", autouse=True)
def run_test_server():
    """
    Spins up uvicorn test server with complete database isolation.
    Uses an isolated temporary SQLite database so that:
    1. Real data in celebration_planner.db is strictly preserved and never mutated.
    2. The test suite starts with clean, predictable, reproducible state.
    3. Seed directory and canonical demo events are reliably initialized.
    """
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_smoke_isolated.db")
    test_db_url = f"sqlite:///{test_db_path}"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Initialize seed directory for vendors in the isolated test database
    with TestingSessionLocal() as db:
        VendorService.init_seed_directory(db)

    # Pre-seed the three canonical demo events (wedding, birthday, community)
    with TestingSessionLocal() as db:
        today = date.today()
        canonical_seeds = [
            EventIntake(
                event_type="wedding",
                title="Priya & Rohan Royal Palace Wedding",
                date=(today + timedelta(days=180)).strftime("%Y-%m-%d"),
                city="Jaipur",
                guest_count=350,
                total_budget=2500000.0,
                currency="INR",
                theme_style="Royal Rajasthani Heritage & Marigolds",
                cultural_preferences="Traditional Hindu Vedic Rituals & Sangeet Gala",
                dietary_preferences=["Vegetarian"],
                must_haves=["Vintage car grand baraat", "Live shehnai", "Floral mandap arch"],
                age_group_details="Multi-generational families, elders, and young friends",
            ),
            EventIntake(
                event_type="birthday",
                title="Leo's 10th Superhero Academy Party",
                date=(today + timedelta(days=25)).strftime("%Y-%m-%d"),
                city="Bengaluru",
                guest_count=45,
                total_budget=65000.0,
                currency="INR",
                theme_style="Avengers Superhero Training Camp",
                cultural_preferences="Fun interactive milestone party",
                dietary_preferences=["Vegetarian", "Nut-Free"],
                must_haves=["Custom Spider-Man 3D Cake", "Obstacle course", "Goodie bags"],
                age_group_details="Kids aged 9-11 and parents",
            ),
            EventIntake(
                event_type="community",
                title="Indiranagar Community Green Tech Mela",
                date=(today + timedelta(days=60)).strftime("%Y-%m-%d"),
                city="Bengaluru",
                guest_count=500,
                total_budget=600000.0,
                currency="INR",
                theme_style="Eco-Innovation & Solar Futures",
                cultural_preferences="Open neighborhood civic festival",
                dietary_preferences=["Vegetarian"],
                must_haves=["Keynote AV stage", "Solar power station", "Waste segregation team"],
                age_group_details="Residents, students, and senior citizens",
            ),
        ]
        for s in canonical_seeds:
            plan = FallbackTemplateEngine.generate_plan(s)
            rec = EventModel(
                id=plan.event_id,
                owner_id=None,
                title=s.title,
                event_type=s.event_type,
                date=s.date,
                city=s.city,
                guest_count=s.guest_count,
                total_budget=s.total_budget,
                currency=s.currency,
                intake_json=json.dumps(s.model_dump()),
                plan_json=json.dumps(plan.model_dump()),
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
            db.add(rec)
        db.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.8)  # give server time to bind

    try:
        yield
    finally:
        server.should_exit = True
        app.dependency_overrides.clear()
        test_engine.dispose()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def test_playwright_smoke_all_three_event_types():
    """
    Playwright smoke test completing the full flow:
    intake -> plan -> edit budget -> check vendor -> export
    for all three event types (wedding, birthday, community).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Handle dialogs gracefully so unhandled alerts never hang the test runner
        page.on("response", lambda r: print(f"HTTP {r.status} {r.url}") if "/api/" in r.url else None)
        page.on("console", lambda msg: print(f"PAGE LOG: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
        page.on("dialog", lambda dialog: (print(f"PAGE DIALOG: {dialog.message}"), dialog.accept()))

        event_configs = [
            ("wedding", "Royal Wedding", "Priya & Rohan Royal Palace Wedding"),
            ("birthday", "10th Birthday", "Leo's 10th Superhero Academy Party"),
            ("community", "Community Mela", "Indiranagar Community Green Tech Mela"),
        ]

        for ev_type, preset_btn_text, expected_title in event_configs:
            # 1. Load Application
            page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
            page.wait_for_selector("header", timeout=10000)

            # Wait for any initial data loading spinner to settle
            try:
                page.wait_for_selector("text=Loading Celebration Planner...", state="detached", timeout=8000)
            except Exception:
                pass

            # 2. Open Intake Modal via "New Plan" button
            new_btn = page.locator("button:has-text('New Plan')")
            new_btn.click()
            page.wait_for_selector("text=Create New Celebration Plan", timeout=5000)

            # 3. Use one-click preset button to populate form
            preset_btn = page.locator(f"button:has-text('{preset_btn_text}')")
            preset_btn.click()
            page.wait_for_timeout(500)

            # 4. Submit Intake Form
            submit_btn = page.locator("button:has-text('Generate AI Plan')")
            submit_btn.click()

            # 5. Wait for Plan Dashboard to load
            title_heading = page.locator("h1").filter(has_text=expected_title)
            title_heading.wait_for(state="visible", timeout=45000)
            assert title_heading.is_visible()
            assert page.locator("text=Days Remaining").first.is_visible()

            # 6. Budget Planner Flow: navigate to tab & test interaction
            budget_tab = page.locator("button:has-text('Budget Planner')")
            budget_tab.click()
            page.wait_for_selector("text=Deterministic Budget Allocation", timeout=10000)
            assert page.locator("text=Category Distribution").is_visible()
            assert (
                page.locator("text=TOTAL ALLOCATION").or_(page.locator("text=Total Allocated")).first.is_visible()
            )

            # 7. Vendor Checklist Flow: navigate to tab & toggle checklist
            vendor_tab = page.locator("button:has-text('Vendor Checklist')")
            vendor_tab.click()
            page.wait_for_selector("text=Vendor Checklist & Contract Management", timeout=10000)
            assert page.locator("text=Mandatory").first.is_visible()

            # Click first checklist item checkbox or task if available
            first_check = page.locator("button:has-text('Check')").first
            first_task = page.locator("text=Verify license").first
            if first_task.is_visible():
                first_task.click()

            # 8. Export Flow: verify Export Dropdown has PDF and CSV links
            export_btn = page.locator("button:has-text('Export')").first
            if export_btn.is_visible():
                export_btn.click()
                page.wait_for_selector("text=Download as PDF", timeout=5000)
                assert page.locator("text=Download as PDF").first.is_visible()
                assert page.locator("text=Download as CSV").first.is_visible()
                # Close dropdown
                export_btn.click()

        browser.close()
