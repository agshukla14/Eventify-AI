import json
import time
import threading
from unittest.mock import MagicMock
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from backend.app.main import app

pytestmark = pytest.mark.playwright

TEST_HOST = "127.0.0.1"
TEST_PORT = 8892


@pytest.fixture(autouse=True)
def fallback_or_mock_gemini_if_exhausted(monkeypatch):
    """
    Auto-detects live Gemini 429 quota exhaustion (500 requests/day exceeded on free tier)
    and mocks recommendations so calculations and UI flows can be tested deterministically.
    """
    try:
        import google.genai.models as genai_models
        real_generate = genai_models.Models.generate_content

        def safe_generate_content(self, *args, **kwargs):
            try:
                return real_generate(self, *args, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    fake_res = MagicMock()
                    prompt_str = str(kwargs.get("contents", args)).lower()
                    preserved = ["Venue & Accommodation"]
                    if "cater" in prompt_str or "food" in prompt_str:
                        preserved.append("Catering & Beverages preserved per host instructions")
                    fake_res.text = json.dumps({
                        "revised_total_budget": 0.0,
                        "category_recommendations": [
                            {"category": "Venue & Accommodation", "weight": 30.0, "reason": "Preserved core venue."},
                            {"category": "Catering & Beverages", "weight": 25.0, "reason": "Streamlined menu."},
                            {"category": "Decoration & Floral", "weight": 15.0, "reason": "Optimized floral."},
                            {"category": "Photography & Videography", "weight": 12.0, "reason": "Standard package."},
                            {"category": "Entertainment & Music", "weight": 10.0, "reason": "Local DJ."},
                            {"category": "Contingency & Emergency Fund", "weight": 8.0, "reason": "Maintained buffer."}
                        ],
                        "where_money_saved": ["Balanced vendor allocations"],
                        "why_recommended": "Optimized budget preserving key event elements",
                        "expenses_preserved": preserved
                    })
                    return fake_res
                raise

        monkeypatch.setattr(genai_models.Models, "generate_content", safe_generate_content)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def run_budget_opt_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def test_playwright_budget_optimizer_flow():
    """
    Playwright E2E test for the AI Smart Budget Optimizer:
    1. Loads the planner UI.
    2. Opens an event's Budget Planner tab.
    3. Verifies Budget Analysis (Health, Highest Expense, Potential Savings).
    4. Submits an optimization prompt (e.g. 'Reduce my wedding budget by ₹30,000').
    5. Verifies AI Comparison View & AI Explanation cards.
    6. Tests 'Discard Changes'.
    7. Submits optimization and clicks 'Apply New Budget'.
    8. Confirms that new budget is persisted and reflected in the UI.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Load app
        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("header", timeout=8000)

        # 2. Open Intake Modal and use preset to create a fresh wedding
        new_btn = page.locator("button:has-text('New Plan')")
        new_btn.click()
        page.wait_for_selector("text=Create New Celebration Plan")

        preset_btn = page.locator("button:has-text('💍 Royal Wedding')")
        preset_btn.click()

        submit_btn = page.locator("button:has-text('Generate AI Plan')")
        submit_btn.click()

        # Wait for Plan to load
        page.wait_for_selector("text=Days Remaining", timeout=12000)

        # 3. Navigate to Budget Planner Tab
        budget_tab = page.locator("button:has-text('Budget Planner')")
        budget_tab.click()

        # 4. Verify Budget Analysis Section is present
        page.wait_for_selector("text=Budget Health", timeout=8000)
        assert page.locator("text=Highest Expense").is_visible()
        assert page.locator("text=High Savings Potential").is_visible()

        # 5. Verify AI Budget Optimizer panel is present
        page.wait_for_selector("text=AI Smart Budget Optimizer", timeout=5000)
        assert page.locator("button:has-text('Reduce my wedding budget by ₹30,000')").is_visible()

        # Click prompt preset which auto-triggers optimizer
        preset_prompt_btn = page.locator("button:has-text('Reduce my wedding budget by ₹30,000')")
        preset_prompt_btn.click()

        # 6. Wait for Optimization Comparison to display
        page.wait_for_selector("text=Optimization Summary", timeout=15000)
        assert page.locator("text=Total Savings").first.is_visible()
        assert page.locator("text=Where Money Was Saved").is_visible()
        assert page.locator("text=Why Recommended").is_visible()
        assert page.locator("text=Important Expenses Preserved").is_visible()
        assert page.locator("text=Side-by-Side Category Allocation Comparison").is_visible()
        assert page.locator("text=Detailed Category Changes & Impact").is_visible()

        # 7. Test Discard Changes
        discard_btn = page.locator("button:has-text('Discard Changes')").first
        assert discard_btn.is_visible()
        discard_btn.click()

        # Verify comparison view is dismissed
        page.wait_for_timeout(500)
        assert not page.locator("text=Optimization Summary").is_visible()

        # 8. Re-trigger optimization via manual prompt & Optimize Budget button
        prompt_input = page.locator("input[placeholder*='Reduce my budget']")
        prompt_input.fill("Reduce my wedding budget by ₹30,000. Keep food quality high!")
        optimize_btn = page.locator("button:has-text('Optimize Budget')")
        optimize_btn.click()

        page.wait_for_selector("text=Optimization Summary", timeout=15000)

        apply_btn = page.locator("button:has-text('Apply New Budget')").first
        assert apply_btn.is_visible()
        apply_btn.click()

        # Verify success toast / notification banner
        page.wait_for_selector("text=Successfully applied optimized budget", timeout=8000)
        assert page.locator("text=Successfully applied optimized budget").is_visible()

        browser.close()
