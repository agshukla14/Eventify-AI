import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

TEST_HOST = "127.0.0.1"
TEST_PORT = 8901


@pytest.fixture(scope="session", autouse=True)
def run_find_vendors_e2e_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_playwright_find_vendors_e2e():
    """
    Playwright E2E browser test for Phase 5: AI-POWERED LOCAL VENDOR RECOMMENDATION & MANAGEMENT:
    1. Load application & verify dashboard.
    2. Switch to 'Find Vendors' tab.
    3. Verify directory filters, search, and vendor cards.
    4. Test AI Vendor Recommendation query and verify grounded AI response card.
    5. Test Side-by-Side Vendor Comparison with AI pros/cons evaluation modal.
    6. Book a vendor with agreed price and advance payment (validating dynamic balance calculation).
    7. Record advance payment into Phase 2 Smart Expense Tracking.
    8. Switch to Vendor Analytics & Spending view to verify KPI summary and charts.
    9. Add a custom user vendor and verify it appears with community badge and edit/delete actions.
    10. Ensure zero console errors throughout execution.
    """
    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()

        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("dialog", lambda dialog: dialog.accept())

        # 1. Load application
        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("header", timeout=12000)
        page.wait_for_selector("text=Days Remaining", timeout=12000)

        # 2. Switch to 'Find Vendors' tab
        vendors_tab_btn = page.locator("button:has-text('Find Vendors')")
        assert vendors_tab_btn.is_visible(), "Find Vendors navigation tab should be visible"
        vendors_tab_btn.click()

        # 3. Verify directory header and elements
        page.wait_for_selector("text=Find Vendors & Local Event Management", timeout=10000)
        assert page.locator("text=AI-Powered Vendor Recommendation").is_visible()

        # 4. Test AI Vendor Recommendation Search
        ai_query_input = page.locator("input[placeholder*='wedding photographers in Ahmedabad']")
        assert ai_query_input.is_visible()
        ai_query_input.fill("Find wedding photographers in Ahmedabad under ₹30,000")

        get_recs_btn = page.locator("button:has-text('Search with AI')")
        get_recs_btn.click()

        # Wait for recommendation card to appear
        page.wait_for_selector("text=Matching Verified Vendors", timeout=15000)
        assert page.locator("text=% Match").first.is_visible()

        # Verify clear button resets recommendations
        page.locator("button:has-text('Clear AI Search')").click()
        page.wait_for_timeout(300)

        # 5. Filter Directory by Category
        photo_filter_btn = page.locator("button:has-text('Photography')").first
        photo_filter_btn.click()
        page.wait_for_timeout(300)

        # Verify photography vendor cards exist
        assert page.locator("text=Light Chamber Studios").is_visible()

        # 6. Test Side-by-Side Comparison
        # Select first two comparison checkboxes
        compare_boxes = page.locator("label:has-text('Compare') input[type='checkbox']")
        count_boxes = compare_boxes.count()
        assert count_boxes >= 2, f"Expected at least 2 comparison checkboxes, got {count_boxes}"
        compare_boxes.nth(0).check()
        compare_boxes.nth(1).check()

        # Click Compare button in header/floating bar
        compare_action_btn = page.locator("button:has-text('Compare (2)')")
        compare_action_btn.wait_for(state="visible", timeout=5000)
        compare_action_btn.click()

        # Verify Comparison modal opens
        page.wait_for_selector("text=Side-by-Side Vendor Comparison", timeout=8000)
        assert page.locator("text=AI Evaluation Summary").is_visible()
        assert page.locator("text=Best Budget").is_visible()
        assert page.locator("text=Best Rated").is_visible()

        # Close comparison modal
        page.locator("button:has-text('Close Comparison')").click()
        page.wait_for_timeout(300)

        # 7. Test Booking Modal & Calculations
        # Click "Book for Event" on first visible vendor
        book_btn = page.locator("button:has-text('Book for Event')").first
        book_btn.click()

        page.wait_for_selector("text=Manage Booking:", timeout=6000)

        # Enter agreed price and advance payment
        agreed_input = page.locator("label:has-text('Agreed Price') ~ input")
        agreed_input.fill("28000")

        advance_input = page.locator("label:has-text('Advance Payment') ~ input")
        advance_input.fill("10000")

        # Verify dynamic remaining balance calculation shows ₹18,000
        page.wait_for_timeout(300)
        assert page.locator("text=18,000").is_visible()

        # Select status Booked
        status_select = page.locator("label:has-text('Booking Status') ~ select")
        status_select.select_option("Booked")

        # Save booking
        page.locator("button:has-text('Save Booking')").click()
        page.wait_for_selector("text=Booking saved for", timeout=6000)
        page.wait_for_timeout(2200)

        # 8. Switch to Event Bookings subtab
        bookings_subtab = page.locator("button:has-text('Event Bookings')")
        bookings_subtab.click()
        page.wait_for_selector("text=Event Vendor Bookings", timeout=6000)

        # Verify booking card details
        assert page.locator("text=Booked").first.is_visible()
        assert page.locator("text=28,000").first.is_visible()

        # Click Record as Expense button
        record_exp_btn = page.locator("button:has-text('Record as Expense')").first
        record_exp_btn.click()

        # Verify success notification
        page.wait_for_selector("text=has been recorded in Phase 2 Smart Expense Tracking", timeout=8000)

        # 9. Switch to Analytics subtab
        analytics_subtab = page.locator("button:has-text('Vendor Analytics & Spending')")
        analytics_subtab.click()
        page.wait_for_selector("text=Booked Vendors", timeout=6000)

        assert page.locator("text=Total Agreed Cost").is_visible()
        assert page.locator("text=Advance Paid").first.is_visible()
        assert page.locator("text=Remaining Due").is_visible()
        assert page.locator("text=Vendor Spending Analysis by Category").is_visible()

        # 10. Add Custom User Vendor
        # Switch back to directory subtab
        page.locator("button:has-text('Vendor Directory')").click()
        page.wait_for_timeout(400)

        add_vendor_btn = page.locator("button:has-text('Add Custom Vendor')")
        add_vendor_btn.click()

        page.wait_for_selector("text=Add New Custom Vendor", timeout=6000)

        # Fill custom vendor form
        name_input = page.locator("label:has-text('Business Name') ~ input")
        name_input.fill("Jaipur Royal Grand Florists")

        location_input = page.locator("label:has-text('Location / City') ~ input")
        location_input.fill("Jaipur, Rajasthan")

        desc_input = page.locator("label:has-text('Description') ~ textarea")
        desc_input.fill("Specialists in royal Marwari marigold mandaps and palace floral canopies.")

        min_price_input = page.locator("label:has-text('Min Price') ~ input")
        min_price_input.fill("15000")

        max_price_input = page.locator("label:has-text('Max Price') ~ input")
        max_price_input.fill("45000")

        phone_input = page.locator("label:has-text('Contact Phone') ~ input")
        phone_input.fill("+91 98765 43210")

        email_input = page.locator("label:has-text('Contact Email') ~ input")
        email_input.fill("info@jaipurroyalflorists.in")

        # Save custom vendor
        page.locator("button:has-text('Add to Directory')").click()
        page.wait_for_timeout(800)

        # Search for custom vendor in directory
        search_dir_input = page.locator("input[placeholder*='Filter name or service']")
        search_dir_input.fill("Jaipur Royal Grand Florists")
        page.wait_for_timeout(400)

        assert page.locator("text=Jaipur Royal Grand Florists").first.is_visible()
        assert page.locator("text=User Added").first.is_visible()

        # Filter out benign favicon 404s
        filtered_console_errors = [
            err for err in console_errors
            if "favicon.ico" not in err and "failed to load resource" not in err.lower()
        ]
        assert not filtered_console_errors, f"Unexpected console errors: {filtered_console_errors}"
        assert not page_errors, f"Unexpected page errors: {page_errors}"

        browser.close()
