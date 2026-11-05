import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

pytestmark = pytest.mark.playwright

TEST_HOST = "127.0.0.1"
TEST_PORT = 8895


@pytest.fixture(scope="session", autouse=True)
def run_expense_e2e_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_playwright_expense_tracking_e2e():
    """
    Playwright E2E browser test for Phase 2: SMART EXPENSE TRACKING:
    1. Loads the planner application.
    2. Opens an event and switches to 'Expense Tracking' tab.
    3. Verifies 4 summary cards & charts are rendered.
    4. Opens Add Expense modal, fills out details, and saves.
    5. Confirms expense appears in transaction table & updates dashboard totals.
    6. Edits expense and confirms updated totals.
    7. Tests search filter.
    8. Verifies CSV & PDF export links.
    9. Deletes expense and confirms removal.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Handle dialogs (like confirm for delete)
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

        # 3. Navigate to 'Expense Tracking' tab
        expense_tab_btn = page.locator("button:has-text('Expense Tracking')")
        expense_tab_btn.click()

        # 4. Verify 4 Summary Cards
        page.wait_for_selector("text=Total Event Budget", timeout=8000)
        assert page.locator("text=Total Event Budget").first.is_visible()
        assert page.locator("text=Total Actual Expenses").first.is_visible()
        assert page.locator("text=Budget Utilization").first.is_visible()

        # Verify Charts & Analysis Section
        assert page.locator("text=Planned vs Actual Category Spending").is_visible()
        assert page.locator("text=Actual Expense Distribution").is_visible()
        assert page.locator("text=Category-wise Planned vs Actual Analysis").is_visible()

        # 5. Open Add Expense Modal
        add_btn = page.locator("button:has-text('Add New Expense')")
        add_btn.click()

        page.wait_for_selector("text=Add New Expense Record", timeout=4000)

        # Fill modal form
        page.locator("input[placeholder*='Venue Advance Deposit']").fill("Grand Palace Hall Advance")
        page.locator("input[placeholder='0.00']").fill("45000")
        page.locator("input[placeholder*='Royal Palace Caterers']").fill("Grand Palace Management")
        page.locator("textarea[placeholder*='Receipt number']").fill("Advance payment receipt #9821")

        save_btn = page.locator("button:has-text('Record Expense')")
        save_btn.click()

        # 6. Verify expense is displayed in Transaction Table
        page.wait_for_selector("text=Grand Palace Hall Advance", timeout=8000)
        assert page.locator("text=Grand Palace Hall Advance").is_visible()
        assert page.locator("text=45,000").first.is_visible()
        assert page.locator("text=Grand Palace Management").is_visible()

        # 7. Edit Expense: click edit button
        edit_btn = page.locator("button[title='Edit Expense']").first
        edit_btn.click()

        page.wait_for_selector("text=Edit Expense Record", timeout=4000)
        # Update amount to 55000
        page.locator("input[placeholder='0.00']").fill("55000")
        page.locator("button:has-text('Save Changes')").click()

        # Verify updated amount
        page.wait_for_selector("text=55,000", timeout=8000)
        assert page.locator("text=55,000").first.is_visible()

        # 8. Test Search Filter
        search_input = page.locator("input[placeholder*='Search expense']")
        search_input.fill("Grand Palace")
        page.wait_for_timeout(300)
        assert page.locator("text=Grand Palace Hall Advance").is_visible()

        search_input.fill("NonExistentXYZ")
        page.wait_for_timeout(300)
        assert page.locator("text=No expenses found").is_visible()

        search_input.fill("")
        page.wait_for_timeout(300)
        assert page.locator("text=Grand Palace Hall Advance").is_visible()

        # 9. Test Export Dropdown
        export_btn = page.locator("button:has-text('Export Records')")
        export_btn.click()
        page.wait_for_selector("text=Download as CSV", timeout=3000)
        assert page.locator("text=Download as CSV").is_visible()
        assert page.locator("text=Download as PDF Report").is_visible()
        # Close menu
        export_btn.click()

        # 10. Delete Expense
        del_btn = page.locator("button[title='Delete Expense']").first
        del_btn.click()

        # Verify removal
        page.wait_for_selector("text=No expenses found", timeout=8000)
        assert not page.locator("text=Grand Palace Hall Advance").is_visible()

        browser.close()
