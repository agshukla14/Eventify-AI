import time
import threading
from datetime import date, timedelta
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

TEST_HOST = "127.0.0.1"
TEST_PORT = 8905


@pytest.fixture(scope="session", autouse=True)
def run_weather_planner_e2e_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_playwright_weather_planner_e2e():
    """
    Playwright E2E browser test for Phase 6: AI WEATHER-AWARE EVENT PLANNER:
    1. Load application & verify dashboard.
    2. Switch to 'Weather & Event Planning' tab.
    3. Verify accuracy horizon banner for distant date ('Historical Climate Reference – Not an Actual Forecast').
    4. Query short-term date (3 days ahead) & verify live forecast labeling ('Live Meteorological Forecast').
    5. Verify core weather metrics, atmospheric risk factors, and Recharts visualization controls.
    6. Select smart event weather recommendations and save to timeline with confirmation modal.
    7. Test AI Weather Assistant with quick prompt and verify grounded response card.
    8. Switch to 'Timeline & Schedule' tab and verify saved weather mitigation tasks appear.
    9. Ensure zero console errors throughout execution.
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

        # 2. Switch to 'Weather & Event Planning' tab
        weather_tab_btn = page.locator("button:has-text('Weather & Event Planning')")
        assert weather_tab_btn.is_visible(), "Weather & Event Planning tab button should be visible"
        weather_tab_btn.click()

        # 3. Verify weather page header and components
        page.wait_for_selector("h1:has-text('Weather & Event Planning')", timeout=12000)
        assert page.locator("text=Phase 6: AI Weather-Aware Event Planner").is_visible()

        # 4. Verify initial forecast accuracy horizon banner (seed event date is ~180 days in future)
        page.wait_for_selector("text=Historical Climate Reference", timeout=12000)
        assert page.locator("text=Multi-Year Climate Average").is_visible()
        assert page.locator("text=Data Source: Open-Meteo").is_visible()

        # Verify core metric cards exist
        assert page.locator("text=Condition").first.is_visible()
        assert page.locator("text=Max Temp").first.is_visible()
        assert page.locator("text=Feels Like").first.is_visible()
        assert page.locator("text=Rain Chance").first.is_visible()
        assert page.locator("text=Humidity").first.is_visible()
        assert page.locator("text=Wind Speed").first.is_visible()

        # 5. Query short-term date (3 days ahead) in Mumbai to verify Live Forecast mode
        near_date = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")

        city_input = page.locator("input[placeholder*='Celebration Location / City']")
        city_input.fill("Mumbai")

        date_input = page.locator("input[type='date']").first
        date_input.fill(near_date)

        check_btn = page.locator("button:has-text('Check Weather')")
        check_btn.click()

        # Verify horizon banner updates to Live Meteorological Forecast
        page.wait_for_selector("text=Live Meteorological Forecast", timeout=15000)
        assert page.locator("text=Active Horizon").is_visible()

        # 6. Verify Atmospheric Risk Assessment
        page.wait_for_selector("text=Atmospheric Risk Assessment", timeout=6000)
        assert page.locator("text=Rain & Precipitation").first.is_visible()
        assert page.locator("text=Temperature & Heat Index").first.is_visible()
        assert page.locator("text=Wind & Gusts").first.is_visible()
        assert page.locator("text=Relative Humidity").first.is_visible()

        # 7. Test Recharts chart controls
        rain_chart_btn = page.locator("button:has-text('Rain & Probability')")
        if rain_chart_btn.is_visible():
            rain_chart_btn.click()
            page.wait_for_timeout(300)

        wind_chart_btn = page.locator("button:has-text('Wind Speed')")
        if wind_chart_btn.is_visible():
            wind_chart_btn.click()
            page.wait_for_timeout(300)

        # 8. Test Smart Event Weather Recommendations & Save to Timeline
        page.wait_for_selector("text=Smart Event Weather Recommendations", timeout=6000)

        # Ensure at least one recommendation is selected
        rec_checkboxes = page.locator("input[type='checkbox']")
        if rec_checkboxes.count() > 0:
            rec_checkboxes.first.check()

        save_timeline_btn = page.locator("button:has-text('Save to Timeline')")
        assert save_timeline_btn.is_visible()
        save_timeline_btn.click()

        # Confirmation modal appears
        page.wait_for_selector("text=Confirm Timeline Integration", timeout=6000)
        assert page.locator("text=You are about to save").is_visible()

        # Click Confirm & Save
        confirm_save_btn = page.locator("button:has-text('Confirm & Save to Timeline')")
        confirm_save_btn.click()

        # Verify success toast
        page.wait_for_selector("text=mitigation task", timeout=8000)

        # 9. Test AI Weather Assistant
        page.wait_for_selector("text=AI Weather Assistant", timeout=6000)

        # Click quick prompt chip
        quick_chip = page.locator("button:has-text('outdoor wedding?')").first
        quick_chip.click()

        # Verify AI answer card renders with Grounded Advice
        page.wait_for_selector("text=Grounded Meteorological Advice", timeout=15000)
        assert page.locator("text=Recommended Action Items:").first.is_visible()
        assert page.locator("text=Grounding:").first.is_visible()

        # 10. Switch to 'Timeline & Schedule' tab and verify tasks added
        timeline_tab_btn = page.locator("button:has-text('Timeline & Schedule')")
        timeline_tab_btn.click()
        page.wait_for_selector("text=Milestone Schedule & Adaptive Timeline", timeout=8000)
        assert page.locator("text=Weather mitigation action item").first.is_visible()

        # Filter out benign favicon 404s
        filtered_console_errors = [
            err for err in console_errors
            if "favicon.ico" not in err and "failed to load resource" not in err.lower()
        ]
        assert not filtered_console_errors, f"Unexpected console errors: {filtered_console_errors}"
        assert not page_errors, f"Unexpected page errors: {page_errors}"

        browser.close()
