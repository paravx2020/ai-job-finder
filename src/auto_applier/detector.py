"""CAPTCHA and anti-bot detection for JobFinder auto-applier.

Detects common CAPTCHA types (reCAPTCHA, hCaptcha, text challenges)
and anti-bot indicators before form submission.

Usage:
    from src.auto_applier.detector import PageDetector

    detector = PageDetector()
    result = detector.detect_captcha(page)
    if result["detected"]:
        logger.info(f"CAPTCHA detected: {result['type']}")
"""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from playwright.sync_api import Page

from src.utils.logging import get_logger

logger = get_logger(__name__)


class CaptchaType(str, Enum):
    """Types of CAPTCHA challenges."""
    RECAPTCHA = "recaptcha"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    TEXT_CHALLENGE = "text_challenge"
    UNKNOWN = "unknown"


class PageDetector:
    """Detects CAPTCHA challenges and anti-bot measures on web pages."""

    # CSS selectors for common CAPTCHA elements
    CAPTCHA_SELECTORS: ClassVar[list[str]] = [
        # reCAPTCHA
        "iframe[src*='recaptcha']",
        "div.g-recaptcha",
        "recaptcha-v3",
        # hCaptcha
        "iframe[src*='hcaptcha']",
        "div.h-captcha",
        # Cloudflare Turnstile
        "iframe[src*='challenges.cloudflare.com']",
        "div.cf-turnstile",
        # Generic CAPTCHA iframes
        "iframe[src*='captcha']",
        "iframe[src*='challenge']",
    ]

    # Text patterns that indicate a CAPTCHA or verification challenge
    CAPTCHA_TEXT_PATTERNS: ClassVar[list[str]] = [
        "verify you are human",
        "verify you're human",
        "prove you're a human",
        "complete the security check",
        "complete the captcha",
        "robot verification",
        "security check",
        "please verify",
        "anti-robot verification",
        "checking your browser",
    ]

    # Anti-bot indicators (URL patterns, page titles)
    ANTI_BOT_INDICATORS: ClassVar[list[str]] = [
        "access denied",
        "blocked",
        "challenge-platform",
        "ddos protection",
        "rate limit",
        "too many requests",
        "suspicious activity",
    ]

    def detect_captcha(self, page: Page) -> dict[str, Any]:
        """Check if the current page contains a CAPTCHA challenge.

        Args:
            page: Playwright Page object.

        Returns:
            Dictionary with keys:
                - detected (bool): Whether a CAPTCHA was found
                - type (CaptchaType|None): Type of CAPTCHA
                - method (str): How it was detected ("selector", "text", "url")
                - details (str): Additional details
        """
        # Method 1: Check for CAPTCHA DOM elements
        for selector in self.CAPTCHA_SELECTORS:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    captcha_type = self._classify_captcha_from_selector(selector)
                    logger.warning("CAPTCHA detected via selector: %s (%s)", selector, captcha_type)
                    return {
                        "detected": True,
                        "type": captcha_type,
                        "method": "selector",
                        "details": f"Found element matching: {selector}",
                    }
            except Exception:
                continue

        # Method 2: Check page text for CAPTCHA keywords
        try:
            page_text = page.inner_text("body").lower()
            for pattern in self.CAPTCHA_TEXT_PATTERNS:
                if pattern in page_text:
                    logger.warning("CAPTCHA detected via text pattern: %s", pattern)
                    return {
                        "detected": True,
                        "type": CaptchaType.TEXT_CHALLENGE,
                        "method": "text",
                        "details": f"Found text pattern: {pattern}",
                    }
        except Exception:
            pass

        # Method 3: Check URL for challenge indicators
        try:
            url = page.url.lower()
            if any(indicator in url for indicator in ["challenge", "captcha", "verify", "turnstile"]):
                logger.warning("CAPTCHA detected via URL pattern: %s", url)
                return {
                    "detected": True,
                    "type": CaptchaType.UNKNOWN,
                    "method": "url",
                    "details": f"URL contains challenge indicator: {url}",
                }
        except Exception:
            pass

        return {"detected": False, "type": None, "method": None, "details": "No CAPTCHA detected"}

    def detect_login_wall(self, page: Page) -> bool:
        """Check if the page requires login before proceeding.

        Args:
            page: Playwright Page object.

        Returns:
            True if a login wall is detected.
        """
        login_indicators = [
            "sign in", "log in", "login", "sign up", "register",
            "create account", "please log in", "authentication required",
        ]

        login_selectors = [
            "input[name='email']",
            "input[name='username']",
            "input[type='password']",
            "form[action*='login']",
            "form[action*='signin']",
        ]

        # Check for login form elements
        for selector in login_selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    logger.warning("Login wall detected via selector: %s", selector)
                    return True
            except Exception:
                continue

        # Check page text
        try:
            page_text = page.inner_text("body").lower()
            for indicator in login_indicators:
                if indicator in page_text:
                    # Only flag if multiple indicators are present (reduce false positives)
                    count = sum(1 for i in login_indicators if i in page_text)
                    if count >= 2:
                        logger.warning("Login wall detected via text (%d indicators)", count)
                        return True
        except Exception:
            pass

        return False

    def detect_rate_limit(self, page: Page) -> bool:
        """Check if the page indicates rate limiting.

        Args:
            page: Playwright Page object.

        Returns:
            True if rate limiting is detected.
        """
        try:
            page_text = page.inner_text("body").lower()
            url = page.url.lower()

            rate_limit_indicators = [
                "too many requests", "rate limit", "rate-limited",
                "slow down", "try again later", "429",
            ]

            for indicator in rate_limit_indicators:
                if indicator in page_text or indicator in url:
                    logger.warning("Rate limit detected: %s", indicator)
                    return True
        except Exception:
            pass

        # Check HTTP status
        try:
            # This requires checking the last response status
            # In practice, this would be passed from the scraper
            pass
        except Exception:
            pass

        return False

    def full_check(self, page: Page) -> dict[str, Any]:
        """Run all detections and return a comprehensive report.

        Args:
            page: Playwright Page object.

        Returns:
            Dictionary with all detection results.
        """
        captcha = self.detect_captcha(page)
        login = self.detect_login_wall(page)
        rate_limit = self.detect_rate_limit(page)

        return {
            "captcha": captcha,
            "login_wall": login,
            "rate_limit": rate_limit,
            "blocked": captcha["detected"] or login or rate_limit,
        }

    @staticmethod
    def _classify_captcha_from_selector(selector: str) -> CaptchaType:
        """Classify the CAPTCHA type based on the CSS selector that matched."""
        if "recaptcha" in selector:
            return CaptchaType.RECAPTCHA
        if "hcaptcha" in selector:
            return CaptchaType.HCAPTCHA
        if "cloudflare" in selector or "turnstile" in selector:
            return CaptchaType.CLOUDFLARE
        return CaptchaType.UNKNOWN
