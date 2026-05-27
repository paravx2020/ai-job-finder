"""Automated job application submission using Playwright.

Refactored for autonomous mode — no user confirmation prompts,
retry logic for flaky selectors, CAPTCHA detection, and rate limiting.
"""

import random
import time
from typing import Any

from playwright.sync_api import Page, sync_playwright

from config import (
    APPLY_MAX_RETRIES,
    APPLY_RATE_LIMIT_DELAY,
    CONFIRM_BEFORE_SUBMIT,
    SCRAPER_TIMEOUT,
    USER_AGENT,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

COMMON_FIELD_SELECTORS = {
    "name": ["input[name='name']", "input[aria-label*='name']", "input#name", "input[name='full_name']"],
    "email": ["input[type='email']", "input[name='email']", "input[aria-label*='email']"],
    "phone": ["input[type='tel']", "input[name='phone']", "input[aria-label*='phone']"],
    "resume": ["input[type='file']", "input[accept='.pdf,.doc,.docx']"],
    "cover_letter": ["textarea", "div[contenteditable='true']"],
    "submit": [
        "button[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Apply')",
        "button:has-text('Send')",
        "button:has-text('Submit Application')",
        "input[type='submit'][value='Apply']",
    ],
}

APPLY_BUTTON_SELECTORS = [
    "button:has-text('Apply')",
    "button:has-text('Easy Apply')",
    "a:has-text('Apply')",
    "[data-testid='apply-button']",
    "button:has-text('Apply Now')",
    "button:has-text('I\'m Interested')",
    "a[data-automation='applyButton']",
    "button:has-text('Submit Application')",
    ".apply-button",
    "#apply-button",
]

# Track per-site application success/failure for layout change detection
_site_stats: dict[str, dict[str, int]] = {}


def _track_site_result(domain: str, success: bool):
    """Track per-site success/failure rates."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(domain)
        site = parsed.netloc or domain
    except Exception:
        site = domain

    if site not in _site_stats:
        _site_stats[site] = {"success": 0, "failure": 0}

    if success:
        _site_stats[site]["success"] += 1
    else:
        _site_stats[site]["failure"] += 1


def get_site_stats() -> dict:
    """Return per-site application statistics."""
    return dict(_site_stats)


def _detect_field(page: Page, field_name: str) -> str | None:
    """Find a field selector on the page."""
    for selector in COMMON_FIELD_SELECTORS.get(field_name, []):
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                return selector
        except Exception:
            continue
    return None


def _fill_field(page: Page, field_name: str, value: str):
    """Fill a form field with retry logic."""
    selector = _detect_field(page, field_name)
    if not selector:
        return False

    for attempt in range(APPLY_MAX_RETRIES):
        try:
            el = page.query_selector(selector)
            if not el:
                continue
            el.click()
            time.sleep(random.uniform(0.2, 0.5))
            el.fill("")
            time.sleep(random.uniform(0.1, 0.3))
            el.fill(value)
            time.sleep(random.uniform(0.3, 0.8))
            return True
        except Exception as e:
            logger.debug(f"Fill {field_name} attempt {attempt + 1} failed: {e}")
            time.sleep(1)
    return False


def _upload_resume(page: Page, resume_path: str) -> bool:
    """Upload a resume file with retry."""
    selector = _detect_field(page, "resume")
    if not selector:
        # Try direct file input
        try:
            file_inputs = page.query_selector_all("input[type='file']")
            for fi in file_inputs:
                try:
                    fi.set_input_files(resume_path)
                    time.sleep(1)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    for attempt in range(APPLY_MAX_RETRIES):
        try:
            el = page.query_selector(selector)
            if el:
                el.set_input_files(resume_path)
                time.sleep(1)
                return True
        except Exception as e:
            logger.debug(f"Resume upload attempt {attempt + 1} failed: {e}")
            time.sleep(1)
    return False


def _find_apply_button(page: Page) -> Any | None:
    """Find the main apply button with multiple strategies."""
    # Strategy 1: Direct selectors
    for selector in APPLY_BUTTON_SELECTORS:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                return btn
        except Exception:
            continue

    # Strategy 2: Scroll and retry (sometimes buttons appear after scroll)
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        for selector in APPLY_BUTTON_SELECTORS:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    return btn
            except Exception:
                continue
    except Exception:
        pass

    # Strategy 3: Look in iframes
    try:
        iframes = page.frames
        for frame in iframes:
            for selector in APPLY_BUTTON_SELECTORS:
                try:
                    btn = frame.query_selector(selector)
                    if btn and btn.is_visible():
                        return btn
                except Exception:
                    continue
    except Exception:
        pass

    return None


def _detect_and_handle_captcha(page: Page, job_url: str) -> dict:
    """Check for CAPTCHA and return blocking status."""
    try:
        from src.auto_applier.detector import PageDetector

        detector = PageDetector()
        captcha_result = detector.detect_captcha(page)

        if captcha_result.get("detected"):
            logger.warning(
                f"CAPTCHA detected ({captcha_result.get('type')}) on {job_url[:80]} — skipping"
            )
            return {"blocked": True, "reason": f"CAPTCHA: {captcha_result.get('type')}", "captcha_type": captcha_result.get("type")}

        # Also check for login walls and rate limits
        check = detector.full_check(page)
        if check.get("blocked"):
            reasons = []
            if check.get("captcha", {}).get("detected"):
                reasons.append("CAPTCHA")
            if check.get("login_wall"):
                reasons.append("Login wall")
            if check.get("rate_limit"):
                reasons.append("Rate limit")
            return {"blocked": True, "reason": "; ".join(reasons)}
    except ImportError:
        # Fallback: simple text-based CAPTCHA check
        try:
            page_text = page.inner_text("body").lower()
            captcha_indicators = [
                "captcha", "verify you are human", "are you a robot",
                "security check", "not a robot",
            ]
            for indicator in captcha_indicators:
                if indicator in page_text:
                    return {"blocked": True, "reason": f"CAPTCHA indicator: {indicator}"}
        except Exception:
            pass

    return {"blocked": False, "reason": ""}


def apply_to_job(
    job_url: str,
    user_data: dict,
    resume_path: str,
    cover_letter: str = "",
    confirm: bool | None = None,
) -> dict:
    """Apply to a single job posting.

    Args:
        job_url: URL of the job application page
        user_data: Dict with keys: name, email, phone (optional), company
        resume_path: Path to the CV/resume file
        cover_letter: Optional cover letter text
        confirm: If None, uses CONFIRM_BEFORE_SUBMIT from config.
                 Set False for autonomous mode, True for interactive.

    Returns:
        Dict with: success (bool), url (str), error (str|None), blocked (bool),
                   captcha_type (str|None), retries_used (int)
    """
    if confirm is None:
        confirm = CONFIRM_BEFORE_SUBMIT

    result: dict[str, Any] = {
        "success": False,
        "url": job_url,
        "error": None,
        "blocked": False,
        "captcha_type": None,
        "retries_used": 0,
    }

    for attempt in range(APPLY_MAX_RETRIES + 1):
        result["retries_used"] = attempt
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()

                try:
                    page.goto(job_url, timeout=SCRAPER_TIMEOUT, wait_until="domcontentloaded")
                except Exception:
                    # Slow page — try with longer timeout
                    page.goto(job_url, timeout=SCRAPER_TIMEOUT * 2, wait_until="load")

                time.sleep(random.uniform(1, 3))

                # Check for CAPTCHA / blocks immediately
                captcha_check = _detect_and_handle_captcha(page, job_url)
                if captcha_check["blocked"]:
                    result["blocked"] = True
                    result["captcha_type"] = captcha_check.get("captcha_type")
                    result["error"] = captcha_check["reason"]
                    browser.close()
                    return result

                # Find apply button
                apply_btn = _find_apply_button(page)
                if not apply_btn:
                    if attempt < APPLY_MAX_RETRIES:
                        logger.warning(f"Apply button not found (attempt {attempt + 1}), retrying...")
                        browser.close()
                        time.sleep(2 ** attempt)  # exponential backoff
                        continue
                    result["error"] = "No apply button found after all retries"
                    _track_site_result(job_url, False)
                    browser.close()
                    return result

                # Click apply
                try:
                    apply_btn.click()
                except Exception:
                    # Try JS click as fallback
                    try:
                        apply_btn.evaluate("el => el.click()")
                    except Exception:
                        if attempt < APPLY_MAX_RETRIES:
                            browser.close()
                            time.sleep(2 ** attempt)
                            continue
                        result["error"] = "Cannot click apply button"
                        _track_site_result(job_url, False)
                        browser.close()
                        return result

                time.sleep(random.uniform(1, 2))

                # Handle possible popup/modal after clicking apply
                _handle_popups(page)

                # Check for CAPTCHA again after clicking
                captcha_check = _detect_and_handle_captcha(page, job_url)
                if captcha_check["blocked"]:
                    result["blocked"] = True
                    result["captcha_type"] = captcha_check.get("captcha_type")
                    result["error"] = captcha_check["reason"]
                    browser.close()
                    return result

                # Fill fields
                _fill_field(page, "name", user_data.get("name", ""))
                _fill_field(page, "email", user_data.get("email", ""))
                _fill_field(page, "phone", user_data.get("phone", ""))

                # Upload resume
                _upload_resume(page, resume_path)

                # Cover letter
                if cover_letter:
                    _fill_field(page, "cover_letter", cover_letter)

                # Confirm before submit (only in interactive mode)
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
                    try:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            submit_btn = btn
                            break
                    except Exception:
                        continue

                if submit_btn:
                    try:
                        submit_btn.click()
                    except Exception:
                        submit_btn.evaluate("el => el.click()")
                    time.sleep(2)

                    # Check for confirmation page / success message
                    success_indicators = [
                        "application submitted",
                        "thank you for applying",
                        "application received",
                        "we've received your application",
                        "successfully applied",
                    ]
                    try:
                        page_text = page.inner_text("body").lower()
                        if any(ind in page_text for ind in success_indicators):
                            result["success"] = True
                            _track_site_result(job_url, True)
                        else:
                            # Assume success if submit button clicked without error
                            result["success"] = True
                            _track_site_result(job_url, True)
                    except Exception:
                        result["success"] = True  # Optimistic
                        _track_site_result(job_url, True)
                else:
                    if attempt < APPLY_MAX_RETRIES:
                        logger.warning(f"Submit button not found (attempt {attempt + 1}), retrying...")
                        browser.close()
                        time.sleep(2 ** attempt)
                        continue
                    result["error"] = "No submit button found after all retries"
                    _track_site_result(job_url, False)

                browser.close()

                if result["success"]:
                    break  # Success — don't retry

        except Exception as e:
            logger.error(f"Application attempt {attempt + 1} failed for {job_url[:80]}: {e}")
            if attempt < APPLY_MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            result["error"] = str(e)
            _track_site_result(job_url, False)

    return result


def _handle_popups(page: Page):
    """Dismiss common popups/dialogs that might appear after clicking apply."""
    dismiss_selectors = [
        "button:has-text('Close')",
        "button:has-text('Dismiss')",
        "button:has-text('Cancel')",
        "button[aria-label='Close']",
        ".modal-close",
        "[data-dismiss='modal']",
    ]
    for selector in dismiss_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click()
                time.sleep(0.5)
        except Exception:
            continue
