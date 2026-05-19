"""Glassdoor job scraper using Playwright."""

from __future__ import annotations

import random
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from config import SCRAPER_DELAY, SCRAPER_TIMEOUT, USER_AGENT
from src.utils.logging import get_logger

from .base import BaseScraper, JobPosting, with_retry

logger = get_logger(__name__)

class GlassdoorScraper(BaseScraper):
    """Scrape job listings from Glassdoor."""

    BASE_URL = "https://www.glassdoor.com"

    @with_retry(max_retries=3)
    def search(self, query: str, location: str = "", max_results: int = 25) -> list[JobPosting]:
        """Search for jobs on Glassdoor.

        Args:
            query: Job search query (e.g., "software engineer").
            location: Location filter (e.g., "New York").
            max_results: Maximum number of results to return.

        Returns:
            List of JobPosting dataclass instances.
        """
        jobs: list[JobPosting] = []
        encoded_query = quote(query)
        encoded_location = quote(location) if location else ""

        url = f"{self.BASE_URL}/Job/jobs.htm?sc.keyword={encoded_query}"
        if location:
            url += f"&locT=C&locKeyword={encoded_location}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            try:
                page.goto(url, timeout=SCRAPER_TIMEOUT, wait_until="domcontentloaded")

                # Dismiss sign-up modal if present
                self._dismiss_modal(page)

                # Scroll to load more results
                self._scroll_results(page)

                # Extract job cards
                cards = page.locator(self.selectors.get("job_card", "[data-test='jobListing']")).all()

                for card in cards[:max_results]:
                    try:
                        job = self._extract_job(card, page)
                        if job:
                            jobs.append(job)
                            # Rate limiting — Glassdoor is aggressive
                            time.sleep(random.uniform(*SCRAPER_DELAY) + 1)
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"[GlassdoorScraper] Error: {e}")
            finally:
                browser.close()

        return jobs

    def source_name(self) -> str:
        return "glassdoor"

    def _dismiss_modal(self, page) -> None:
        """Dismiss the sign-up/login modal if it appears."""
        try:
            # Try common close buttons
            close_selectors = [
                "[data-test='SigninModal'] [data-test='closeButton']",
                ".modalClose",
                "button[aria-label='Close']",
                ".css-1q2z47y",  # Glassdoor close button class
            ]
            for selector in close_selectors:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    time.sleep(1)
                    return
        except Exception:
            pass

    def _scroll_results(self, page) -> None:
        """Scroll the results container to load more listings."""
        scroll_container = self.selectors.get("scroll_container", "[data-test='JobListingResults']")
        try:
            container = page.locator(scroll_container).first
            if container.is_visible(timeout=3000):
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(1.5)
        except Exception:
            # Fallback: scroll the whole page
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(1.5)

    def _extract_job(self, card, page) -> JobPosting | None:
        """Extract job details from a single card element."""
        try:
            # Title and link
            title_el = card.locator(self.selectors.get("title", "[data-test='jobLink']")).first
            title = title_el.inner_text(timeout=2000).strip()
            href = title_el.get_attribute("href", timeout=1000)
            url = f"{self.BASE_URL}{href}" if href and href.startswith("/") else href

            # Company
            company_el = card.locator(self.selectors.get("company", "[data-test='employerName']")).first
            company = company_el.inner_text(timeout=1000).strip()

            # Location
            location_el = card.locator(self.selectors.get("location", "[data-test='location']")).first
            location = location_el.inner_text(timeout=1000).strip()

            # Salary (optional)
            salary = ""
            try:
                salary_el = card.locator(self.selectors.get("salary", "[data-test='salarySource']")).first
                salary = salary_el.inner_text(timeout=1000).strip()
            except Exception:
                pass

            # Description — click the card to load details
            description = ""
            try:
                title_el.click(timeout=2000)
                time.sleep(1.5)
                desc_el = page.locator(self.selectors.get("description", "[data-test='jobDescriptionContent']")).first
                description = desc_el.inner_text(timeout=3000).strip()
            except Exception:
                pass

            if not title or not company:
                return None

            return JobPosting(
                title=title,
                company=company,
                description=description,
                url=url or "",
                source=self.source_name(),
                salary=salary if salary else None,
                location=location if location else None,
            )
        except Exception:
            return None
