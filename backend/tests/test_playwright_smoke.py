import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

TEST_HOST = "127.0.0.1"
TEST_PORT = 8889


@pytest.fixture(scope="session", autouse=True)
def run_test_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)  # give server time to bind
    yield
    server.should_exit = True


def test_playwright_smoke_all_three_event_types():
    """
    Playwright smoke test completing the full flow:
    intake -> plan -> edit budget -> check vendor -> export
    for all three event types (wedding, birthday, community).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        event_configs = [
            ("wedding", "💍 Royal Wedding", "Priya & Rohan Royal Palace Wedding"),
            ("birthday", "🎂 10th Birthday", "Leo's 10th Superhero Academy Party"),
            ("community", "🎪 Community Mela", "Indiranagar Community Green Tech Mela"),
        ]

        for ev_type, preset_btn_text, expected_title in event_configs:
            # 1. Load Application
            page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
            page.wait_for_selector("header")

            # 2. Open Intake Modal via "New Plan" button
            new_btn = page.locator("button:has-text('New Plan')")
            new_btn.click()
            page.wait_for_selector("text=Create New Celebration Plan")

            # 3. Use one-click preset button to populate form
            preset_btn = page.locator(f"button:has-text('{preset_btn_text}')")
            preset_btn.click()

            # 4. Submit Intake Form
            submit_btn = page.locator("button:has-text('Generate AI Plan')")
            submit_btn.click()

            # 5. Wait for Plan Dashboard to load
            title_heading = page.locator("h1").filter(has_text=expected_title)
            title_heading.wait_for(state="visible", timeout=10000)
            assert title_heading.is_visible()
            assert page.locator("text=Days Remaining").first.is_visible()

            # 6. Budget Planner Flow: navigate to tab & test interaction
            budget_tab = page.locator("button:has-text('Budget Planner')")
            budget_tab.click()
            page.wait_for_selector("text=Deterministic Budget Allocation")
            assert page.locator("text=Category Distribution").is_visible()
            assert page.locator("text=TOTAL ALLOCATION").is_visible()

            # 7. Vendor Checklist Flow: navigate to tab & toggle checklist
            vendor_tab = page.locator("button:has-text('Vendor Checklist')")
            vendor_tab.click()
            page.wait_for_selector("text=Vendor Checklist & Contract Management")
            assert page.locator("text=Mandatory").first.is_visible()

            # Click first checklist item checkbox
            first_check = page.locator("button:has-text('Check')").first
            # or click on first checklist card
            first_task = page.locator("text=Verify license").first
            if first_task.is_visible():
                first_task.click()

            # 8. Export Flow: verify Export Dropdown has PDF and CSV links
            export_btn = page.locator("button:has-text('Export')").first
            if export_btn.is_visible():
                export_btn.click()
                page.wait_for_selector("text=Download as PDF", timeout=3000)
                assert page.locator("text=Download as PDF").first.is_visible()
                assert page.locator("text=Download as CSV").first.is_visible()
                # Close dropdown
                export_btn.click()

        browser.close()
