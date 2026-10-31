import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

TEST_HOST = "127.0.0.1"
TEST_PORT = 8898


@pytest.fixture(scope="session", autouse=True)
def run_guests_e2e_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_playwright_guest_management_e2e():
    """
    Playwright E2E browser test for Phase 3: GUEST MANAGEMENT & RSVP SYSTEM:
    1. Loads the planner application.
    2. Switches to 'Guest Management' tab.
    3. Verifies 4 summary cards & charts are rendered.
    4. Opens Add Guest modal, fills out details, and saves.
    5. Confirms guest appears in table & updates dashboard totals.
    6. Updates RSVP status to 'Accepted' and confirms attendance calculations.
    7. Tests search and filter.
    8. Verifies CSV & PDF export links.
    9. Deletes guest and confirms removal.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Handle dialogs
        page.on("dialog", lambda dialog: dialog.accept())

        # 1. Load app
        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("header", timeout=8000)

        # 2. Create fresh event for clean test
        new_btn = page.locator("button:has-text('New Plan')")
        new_btn.click()
        page.wait_for_selector("text=Create New Celebration Plan")

        preset_btn = page.locator("button:has-text('💍 Royal Wedding')")
        preset_btn.click()

        submit_btn = page.locator("button:has-text('Generate AI Plan')")
        submit_btn.click()

        page.wait_for_selector("text=Days Remaining", timeout=12000)

        # 3. Navigate to 'Guest Management' tab
        guest_tab_btn = page.locator("button:has-text('Guest Management')")
        guest_tab_btn.click()

        # 4. Verify 4 Summary Cards
        page.wait_for_selector("text=Total Invited", timeout=8000)
        assert page.locator("text=Total Invited").first.is_visible()
        assert page.locator("text=Confirmed Attendance").first.is_visible()
        assert page.locator("text=Pending Responses").first.is_visible()
        assert page.locator("text=Declined Invitations").first.is_visible()

        # Verify Charts & Analytics Section
        assert page.locator("text=RSVP Response Distribution").is_visible()
        assert page.locator("text=Category Breakdown").is_visible()
        assert page.locator("text=Invitation Pacing").is_visible()

        # 5. Open Add Guest Modal
        add_btn = page.locator("button:has-text('Add New Guest')").first
        add_btn.click()

        page.wait_for_selector("text=Add New Guest", timeout=4000)

        # Fill modal form
        page.locator("input[placeholder*='Rahul Sharma']").fill("Dr. Ananya Roy")
        page.locator("input[placeholder*='name@example.com']").fill("ananya.roy@example.com")
        page.locator("input[placeholder*='+91-9876543210']").fill("+91-9876500001")
        page.locator("input[placeholder*='Jain vegetarian']").fill("Vegan meal preference")

        save_btn = page.locator("button:has-text('Save Guest Record')")
        save_btn.click()

        # 6. Verify guest is displayed in Guest Registry Table
        page.wait_for_selector("text=Dr. Ananya Roy", timeout=8000)
        assert page.locator("text=Dr. Ananya Roy").is_visible()
        assert page.locator("text=ananya.roy@example.com").is_visible()

        # 7. Update RSVP status to 'Accepted'
        # Target the RSVP select dropdown in the table body
        rsvp_select = page.locator("tbody select").first
        rsvp_select.select_option("Accepted")

        # Verify status changed and headcount updated
        page.wait_for_timeout(1000)
        assert page.locator("text=1 Headcount").first.is_visible()

        # 8. Test Search Filter
        search_input = page.locator("input[placeholder*='Search guest']")
        search_input.fill("Ananya")
        page.wait_for_timeout(300)
        assert page.locator("text=Dr. Ananya Roy").is_visible()

        search_input.fill("NonExistentXYZ")
        page.wait_for_timeout(300)
        assert page.locator("text=No guests found").is_visible()

        search_input.fill("")
        page.wait_for_timeout(300)
        assert page.locator("text=Dr. Ananya Roy").is_visible()

        # 9. Test CSV Import Modal opening
        import_btn = page.locator("button:has-text('Import CSV')")
        import_btn.click()
        page.wait_for_selector("text=Import Guest List from CSV", timeout=3000)
        assert page.locator("text=Choose a CSV file").is_visible()
        # Close import modal
        page.locator("button:has-text('Cancel')").first.click()

        # 10. Test Export Dropdown
        export_btn = page.locator("button:has-text('Export Guests')")
        export_btn.click()
        page.wait_for_selector("text=All Guests (CSV)", timeout=3000)
        assert page.locator("text=All Guests (CSV)").is_visible()
        assert page.locator("text=Accepted Guests (CSV)").is_visible()
        assert page.locator("text=Complete Guest Report (PDF)").is_visible()
        # Close menu
        export_btn.click()

        # 11. Delete Guest
        del_btn = page.locator("button[title='Delete Guest']").first
        del_btn.click()

        # Verify removal
        page.wait_for_selector("text=No guests found", timeout=8000)
        assert not page.locator("text=Dr. Ananya Roy").is_visible()

        browser.close()
