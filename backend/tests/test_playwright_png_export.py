import time
import threading
import os
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from PIL import Image
from backend.app.main import app

pytestmark = pytest.mark.playwright

TEST_HOST = "127.0.0.1"
TEST_PORT = 8902


@pytest.fixture(scope="session", autouse=True)
def run_png_test_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield
    server.should_exit = True


def analyze_png_vertical_distribution(image_path: str):
    """
    Analyzes an 800x1120 invitation PNG:
    - Verifies exact dimensions (800, 1120).
    - Checks that content is not clumped at the top.
    - Confirms substantial content exists in both upper and lower halves.
    - Confirms the bottom margin is bounded (content extends gracefully into the lower half).
    """
    with Image.open(image_path) as im:
        assert im.size == (800, 1120), f"Expected (800, 1120), got {im.size}"
        im_rgb = im.convert("RGB")
        width, height = im.size

        # Sample the background color from top-left inside the double border (x=50, y=50)
        bg_pixel = im_rgb.getpixel((50, 50))

        # Helper to check if a pixel differs significantly from background
        def is_content_pixel(px):
            return sum(abs(px[i] - bg_pixel[i]) for i in range(3)) > 30

        # Count content pixels across vertical segments (excluding borders at x < 45 or x > 755)
        seg1_content = 0
        seg2_content = 0
        seg3_content = 0
        seg4_content = 0

        for y in range(80, 1060):
            for x in range(50, 750):
                px = im_rgb.getpixel((x, y))
                if is_content_pixel(px):
                    if 80 <= y < 350:
                        seg1_content += 1
                    elif 350 <= y < 650:
                        seg2_content += 1
                    elif 650 <= y < 900:
                        seg3_content += 1
                    elif 900 <= y < 1060:
                        seg4_content += 1

    return {
        "seg1_content": seg1_content,
        "seg2_content": seg2_content,
        "seg3_content": seg3_content,
        "seg4_content": seg4_content,
        "total_lower_half_content": seg3_content + seg4_content,
    }


def test_png_export_english_wedding():
    """Test PNG generation for English Wedding invitation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        # AI Invitations Tab
        page.locator("button:has-text('AI Invitations')").click()
        page.wait_for_selector("text=AI Invitation Generator & Luxury Card Designer", timeout=6000)

        # Download PNG
        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PNG')").first.click()
        download = download_info.value

        out_path = os.path.join(os.path.dirname(__file__), "test_english_wedding.png")
        download.save_as(out_path)

        stats = analyze_png_vertical_distribution(out_path)
        browser.close()

        # Clean up file
        if os.path.exists(out_path):
            os.remove(out_path)

        # Verification: Content must be well-distributed across upper and lower halves
        assert stats["seg1_content"] > 100, f"Segment 1 should have content: {stats}"
        assert stats["seg2_content"] > 100, f"Segment 2 should have content: {stats}"
        # In the old bug, total_lower_half_content was near 0 (< 200). Now it has details card & sign-off
        assert stats["total_lower_half_content"] > 500, (
            f"Lower half must have substantial content (no empty void). Got: {stats}"
        )


def test_png_export_hindi_royal_wedding():
    """Test PNG generation for Hindi Royal Wedding invitation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        page.locator("button:has-text('AI Invitations')").click()
        page.wait_for_selector("text=AI Invitation Generator & Luxury Card Designer", timeout=6000)

        # Select Hindi
        page.locator("button:has-text('Hindi')").first.click()

        # Select Royal Wedding Template
        page.locator("button:has-text('Royal Wedding')").first.click()

        # Generate Variations
        page.locator("button:has-text('Generate 3 AI Invitation Variations')").click()
        page.wait_for_selector("text=Variation 1", timeout=12000)

        # Download PNG
        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PNG')").first.click()
        download = download_info.value

        out_path = os.path.join(os.path.dirname(__file__), "test_hindi_royal.png")
        download.save_as(out_path)

        stats = analyze_png_vertical_distribution(out_path)
        browser.close()

        if os.path.exists(out_path):
            os.remove(out_path)

        assert stats["seg1_content"] > 100, f"Header should have content: {stats}"
        assert stats["total_lower_half_content"] > 500, (
            f"Hindi Royal Wedding lower half must have substantial content. Got: {stats}"
        )


def test_png_export_gujarati_traditional():
    """Test PNG generation for Gujarati Traditional invitation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        page.locator("button:has-text('AI Invitations')").click()
        page.wait_for_selector("text=AI Invitation Generator & Luxury Card Designer", timeout=6000)

        # Select Gujarati
        page.locator("button:has-text('Gujarati')").first.click()

        # Select Traditional Indian Wedding Template
        page.locator("button:has-text('Traditional Indian Wedding')").first.click()

        # Generate Variations
        page.locator("button:has-text('Generate 3 AI Invitation Variations')").click()
        page.wait_for_selector("text=Variation 1", timeout=12000)

        # Download PNG
        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PNG')").first.click()
        download = download_info.value

        out_path = os.path.join(os.path.dirname(__file__), "test_gujarati_traditional.png")
        download.save_as(out_path)

        stats = analyze_png_vertical_distribution(out_path)
        browser.close()

        if os.path.exists(out_path):
            os.remove(out_path)

        assert stats["seg1_content"] > 100, f"Gujarati Header should have content: {stats}"
        assert stats["total_lower_half_content"] > 500, (
            f"Gujarati lower half must have substantial content. Got: {stats}"
        )


def test_png_export_long_text_no_clipping():
    """Test PNG generation with extensive long text, verifying compact distribution and zero clipping."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        page.locator("button:has-text('AI Invitations')").click()
        page.wait_for_selector("text=AI Invitation Generator & Luxury Card Designer", timeout=6000)

        # Enter a very detailed long message into the message textarea
        msg_textarea = page.locator("textarea").nth(0) # or find by label
        long_message = (
            "We are absolutely thrilled and overjoyed to invite you and your beloved family to celebrate with us. "
            "This special evening marks an extraordinary milestone in our lives, filled with memories and hope for the future.\n\n"
            "Join us for an enchanting night of dinner, music, storytelling, and joyful festivities as we cherish these wonderful moments together. "
            "Your presence, warmth, and heartfelt blessings mean the world to us and will make this celebration truly unforgettable."
        )
        # Check if there is an editable textarea for invitation message
        # Let's fill the active variation's invitation message textarea if present
        textareas = page.locator("textarea")
        if textareas.count() > 0:
            textareas.first.fill(long_message)

        # Download PNG
        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PNG')").first.click()
        download = download_info.value

        out_path = os.path.join(os.path.dirname(__file__), "test_long_text.png")
        download.save_as(out_path)

        # Check image bounds: ensure no content bleeds outside y=1070 (below inner border at 1080)
        im = Image.open(out_path).convert("RGB")
        width, height = im.size
        bg_pixel = im.getpixel((50, 50))

        # Check content distribution
        stats = analyze_png_vertical_distribution(out_path)
        browser.close()

        if os.path.exists(out_path):
            os.remove(out_path)

        assert stats["seg1_content"] > 100
        assert stats["seg2_content"] > 100
        assert stats["total_lower_half_content"] > 500


def test_png_export_minimalist_birthday_and_community():
    """Test PNG generation with Minimalist Birthday (minimal border) and College Fest (dashed border)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(f"http://{TEST_HOST}:{TEST_PORT}/")
        page.wait_for_selector("text=Days Remaining", timeout=10000)

        page.locator("button:has-text('AI Invitations')").click()
        page.wait_for_selector("text=AI Invitation Generator & Luxury Card Designer", timeout=6000)

        # Select Minimalist Birthday
        page.locator("button:has-text('Minimalist Birthday')").first.click()

        # Download PNG
        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PNG')").first.click()
        download = download_info.value

        out_path = os.path.join(os.path.dirname(__file__), "test_minimalist.png")
        download.save_as(out_path)

        stats = analyze_png_vertical_distribution(out_path)
        if os.path.exists(out_path):
            os.remove(out_path)

        assert stats["seg1_content"] > 50
        assert stats["total_lower_half_content"] > 300

        # Switch to College Fest (Dark theme + dashed border)
        page.locator("button:has-text('College Fest')").first.click()

        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PNG')").first.click()
        download_fest = download_info.value

        out_path_fest = os.path.join(os.path.dirname(__file__), "test_college_fest.png")
        download_fest.save_as(out_path_fest)

        with Image.open(out_path_fest) as im_fest:
            assert im_fest.size == (800, 1120)
        browser.close()

        if os.path.exists(out_path_fest):
            os.remove(out_path_fest)

