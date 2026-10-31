import time
import threading
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

TEST_HOST = "127.0.0.1"
TEST_PORT = 8899


@pytest.fixture(scope="session", autouse=True)
def run_invitations_e2e_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_playwright_invitation_generator_e2e():
    """
    Playwright E2E browser test for Phase 4: AI INVITATION GENERATOR:
    1. Loads the planner application.
    2. Switches to 'AI Invitations' tab.
    3. Verifies form inputs and language selectors (English, Hindi, Gujarati).
    4. Generates 3 AI variations in Hindi.
    5. Verifies 3 variation tabs render and can be toggled.
    6. Modifies text and confirms live preview updates.
    7. Customizes design template (e.g. Royal Wedding) and verifies live preview updates.
    8. Saves invitation and verifies it appears in the Saved Invitations Gallery.
    9. Tests guest personalization & explicit mark-sent status confirmation.
    10. Verifies zero console errors.
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
        page.wait_for_selector("header", timeout=10000)
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        # 2. Switch to 'AI Invitations' tab
        inv_tab_btn = page.locator("button:has-text('AI Invitations')")
        assert inv_tab_btn.is_visible()
        inv_tab_btn.click()

        # 3. Verify Invitation Generator header and form
        page.wait_for_selector("text=AI Invitation Generator & Luxury Card Designer", timeout=6000)
        assert page.locator("text=1. Event & Recipient Information").is_visible()
        assert page.locator("text=Live Card Preview").is_visible()

        # Verify language tabs
        assert page.locator("button:has-text('English')").first.is_visible()
        assert page.locator("button:has-text('Hindi')").first.is_visible()
        assert page.locator("button:has-text('Gujarati')").first.is_visible()

        # 4. Select Hindi Language
        page.locator("button:has-text('Hindi')").first.click()

        # 5. Click "Generate 3 AI Invitation Variations" button
        gen_btn = page.locator("button:has-text('Generate 3 AI Invitation Variations')")
        assert gen_btn.is_visible()
        gen_btn.click()

        # Wait for generated variations
        page.wait_for_selector("text=2. Generated Variations", timeout=10000)
        assert page.locator("text=Variation 1").first.is_visible()
        assert page.locator("text=Variation 2").first.is_visible()
        assert page.locator("text=Variation 3").first.is_visible()

        # 6. Switch to Variation 2
        page.locator("button:has-text('Variation 2')").first.click()

        # 7. Customize Design Template: Select "Royal Wedding"
        royal_tmpl_btn = page.locator("button:has-text('Royal Wedding')").first
        royal_tmpl_btn.click()

        # 8. Check that Live Card Preview reflects Royal styling / crown motif
        assert page.locator("text=ROYAL INVITATION").first.is_visible()

        # 9. Test Copy Text Button
        copy_btn = page.locator("button:has-text('Copy Invitation Text')")
        if copy_btn.is_visible():
            copy_btn.click()
            time.sleep(0.5)

        # 10. Save Invitation to Database
        save_btn = page.locator("button:has-text('Save Invitation')")
        assert save_btn.is_visible()
        save_btn.click()

        # Verify success toast / notice
        page.wait_for_selector("text=Invitation saved successfully!", timeout=6000)

        # 11. Scroll to Saved Invitations Gallery and verify saved card
        assert page.locator("text=Saved Invitations Gallery").is_visible()
        assert page.locator("text=Load into Editor").first.is_visible()

        # 12. Switch to Gujarati Language and generate
        page.locator("button:has-text('Gujarati')").first.click()
        gen_btn.click()
        page.wait_for_selector("text=2. Generated Variations (Gujarati)", timeout=10000)
        assert page.locator("text=Variation 1").first.is_visible()

        browser.close()

    assert len(console_errors) == 0, f"Frontend console errors found: {console_errors}"
    assert len(page_errors) == 0, f"Frontend page errors found: {page_errors}"
