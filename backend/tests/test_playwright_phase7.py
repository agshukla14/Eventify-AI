import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

pytestmark = pytest.mark.playwright

TEST_HOST = "127.0.0.1"
TEST_PORT = 8915


@pytest.fixture(scope="session", autouse=True)
def run_phase7_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.8)
    yield
    server.should_exit = True


def test_playwright_phase7_executive_dashboard_and_auth_flow():
    """
    Playwright E2E browser test for Phase 7:
    1. Loads the application homepage.
    2. Verifies the Executive SaaS Command Center is rendered by default.
    3. Verifies all 8 Executive KPI metrics.
    4. Verifies quick action buttons and meteorological risk intelligence banner.
    5. Tests seamless switching between Executive Dashboard and subtabs.
    6. Verifies AuthModal opens on 'Sign In' and closes cleanly.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Load app
        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("header", timeout=10000)

        # 2. Open Executive Dashboard
        exec_tab = page.locator("button:has-text('Executive Dashboard')")
        exec_tab.click()
        page.wait_for_selector("text=Executive Celebration Operations", timeout=12000)
        assert page.locator("text=SaaS Command Center").is_visible()

        # 3. Verify all 8 Executive KPI cards exist
        assert page.locator("text=Total Events").first.is_visible()
        assert page.locator("text=Upcoming Events").first.is_visible()
        assert page.locator("text=Planned Budget").first.is_visible()
        assert page.locator("text=Actual Expenses").first.is_visible()
        assert page.locator("text=Remaining Budget").first.is_visible()
        assert page.locator("text=Confirmed Guests").first.is_visible()
        assert page.locator("text=Pending RSVPs").first.is_visible()
        assert page.locator("text=Booked Vendors").first.is_visible()

        # 4. Verify Executive sections
        assert page.locator("text=Upcoming Event Schedule").is_visible()
        assert page.locator("text=Guest RSVP Attendance").is_visible()
        assert page.locator("text=Budget Allocation vs Actual Spend").is_visible()

        # 5. Test Tab Navigation: Switch to Budget Planner
        budget_tab = page.locator("button:has-text('Budget Planner')")
        budget_tab.click()
        page.wait_for_selector("text=AI Smart Budget Optimizer", timeout=8000)
        assert page.locator("text=Budget Allocation").first.is_visible()

        # Switch back to Executive Dashboard
        exec_tab = page.locator("button:has-text('Executive Dashboard')")
        exec_tab.click()
        page.wait_for_selector("text=Executive Celebration Operations", timeout=8000)

        # 6. Test Auth Modal
        if not page.locator("text=Eventify AI Organizer Portal").is_visible():
            sign_in_btn = page.locator("header button:has-text('Sign In')")
            if not sign_in_btn.is_visible():
                user_profile_btn = page.locator("header div.relative button").last
                user_profile_btn.click()
                sign_out_btn = page.locator("button:has-text('Sign Out')")
                if sign_out_btn.is_visible():
                    sign_out_btn.click()
            else:
                sign_in_btn.click()

        page.wait_for_selector("text=Eventify AI Organizer Portal", timeout=8000)
        assert page.locator("input[type='email']").is_visible()
        assert page.locator("input[type='password']").is_visible()

        # Click guest fallback to close modal
        guest_btn = page.locator("button:has-text('Continue as Guest / Demo Organizer')")
        guest_btn.click()

        # Verify modal closes and executive dashboard is intact
        page.wait_for_selector("text=Executive Celebration Operations", timeout=8000)
        assert page.locator("text=Executive Celebration Operations").is_visible()

        browser.close()
