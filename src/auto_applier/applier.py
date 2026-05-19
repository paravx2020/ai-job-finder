"""Automated job application submission using Playwright."""

import time
import random
from typing import Optional

from playwright.sync_api import sync_playwright, Page

from config import SCRAPER_TIMEOUT, USER_AGENT, CONFIRM_BEFORE_SUBMIT
from src.utils.logging import get_logger
logger = get_logger(__name__)

COMMON_FIELD_SELECTORS = {
    "name": ["input[name='name']", "input[aria-label*='name']", "input#name"],
    "email": ["input[type='email']", "input[name='email']", "input[aria-label*='email']"],
    "phone": ["input[type='tel']", "input[name='phone']", "input[aria-label*='phone']"],
    "resume": ["input[type='file']", "input[accept='.pdf,.doc,.docx']"],
    "cover_letter": ["textarea", "div[contenteditable='true']"],
    "submit": [
        "button[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Apply')",
        "button:has-text('Send')",
    ],
}


def _detect_field(page: Page, field_name: str) -> Optional[str]:
    """Find a field selector on the page."""
    for selector in COMMON_FIELD_SELECTORS.get(field_name, []):
        el = page.query_selector(selector)
        if el and el.is_visible():
            return selector
    return None


def _fill_field(page: Page, field_name: str, value: str):
    selector = _detect_field(page, field_name)
    if selector:
        el = page.query_selector(selector)
        if el:
            el.click()
            el.fill("")
            el.fill(value)
            time.sleep(random.uniform(0.3, 0.8))


def _upload_resume(page: Page, resume_path: str) -> bool:
    selector = _detect_field(page, "resume")
    if selector:
        el = page.query_selector(selector)
        if el:
            el.set_input_files(resume_path)
            time.sleep(1)
            return True
    return False


def apply_to_job(
    job_url: str,
    user_data: dict,
    resume_path: str,
    cover_letter: str = "",
    confirm: bool = CONFIRM_BEFORE_SUBMIT,
) -> dict:
    """Apply to a single job posting. Returns status dict."""
    result = {"success": False, "url": job_url, "error": None}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not confirm)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            page.goto(job_url, timeout=SCRAPER_TIMEOUT)
            time.sleep(random.uniform(1, 3))

            # Look for apply button
            apply_btn = None
            for selector in [
                "button:has-text('Apply')",
                "button:has-text('Easy Apply')",
                "a:has-text('Apply')",
                "[data-testid='apply-button']",
            ]:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    apply_btn = btn
                    break

            if not apply_btn:
                result["error"] = "No apply button found"
                browser.close()
                return result

            apply_btn.click()
            time.sleep(random.uniform(1, 2))

            # Fill fields
            _fill_field(page, "name", user_data.get("name", ""))
            _fill_field(page, "email", user_data.get("email", ""))
            _fill_field(page, "phone", user_data.get("phone", ""))

            # Upload resume
            _upload_resume(page, resume_path)

            # Cover letter
            if cover_letter:
                _fill_field(page, "cover_letter", cover_letter)

            # Confirm before submit
            if confirm:
                logger.info(f"Job URL: {job_url}")
                logger.info(f"Company: {user_data.get('company', 'Unknown')}")
                proceed = input("  Submit application? (y/N): ").strip().lower()
                if proceed != "y":
                    result["error"] = "Skipped by user"
                    browser.close()
                    return result

            # Submit
            submit_btn = None
            for selector in COMMON_FIELD_SELECTORS["submit"]:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    submit_btn = btn
                    break

            if submit_btn:
                submit_btn.click()
                time.sleep(2)
                result["success"] = True
            else:
                result["error"] = "No submit button found"

            browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result
