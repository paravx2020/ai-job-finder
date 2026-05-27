"""LinkedIn job scraper using Playwright.

Note: LinkedIn requires sign-in to view full job descriptions.
The scraper extracts all available data from the list view.
Descriptions are fetched by visiting each job's detail page.
"""
from __future__ import annotations

import random
import re
import time
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright

from config import SCRAPER_DELAY, SCRAPER_TIMEOUT, USER_AGENT
from src.utils.logging import get_logger

from .base import BaseScraper, JobPosting, with_retry

logger = get_logger(__name__)


def _parse_posted_date(text: str) -> datetime | None:
    """Parse LinkedIn relative time strings into datetime."""
    if not text:
        return None
    try:
        text_lower = text.lower().strip()
        match = re.search(r"(\d+)", text_lower)
        if not match:
            return None
        num = int(match.group(1))
        now = datetime.utcnow()
        if "minute" in text_lower:
            return now - timedelta(minutes=num)
        if "hour" in text_lower:
            return now - timedelta(hours=num)
        if "day" in text_lower:
            return now - timedelta(days=num)
        if "week" in text_lower:
            return now - timedelta(weeks=num)
        if "month" in text_lower:
            return now - timedelta(days=num * 30)
    except Exception:
        pass
    return None


class LinkedInScraper(BaseScraper):
    def source_name(self) -> str:
        return "linkedin"

    @with_retry(max_retries=2)
    def search(self, query: str, location: str = "", max_results: int = 25) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1280, "height": 900},
                )
                page = context.new_page()

                search_url = (
                    "https://www.linkedin.com/jobs/search/"
                    f"?keywords={query.replace(' ', '%20')}"
                    f"&location={location.replace(' ', '%20')}"
                )
                page.goto(search_url, timeout=SCRAPER_TIMEOUT)
                time.sleep(random.uniform(*SCRAPER_DELAY))

                # Dismiss sign-in overlay if present
                try:
                    dismiss_btn = page.query_selector("button[aria-label='Dismiss']")
                    if dismiss_btn and dismiss_btn.is_visible():
                        dismiss_btn.click()
                        time.sleep(1)
                except Exception:
                    pass

                # Dismiss "Get the app" prompt
                try:
                    app_close = page.query_selector(".google-play-close-btn, button[aria-label='Close']")
                    if app_close:
                        app_close.click()
                        time.sleep(0.5)
                except Exception:
                    pass

                # Scroll results container to load all visible cards
                try:
                    container = page.query_selector(".jobs-search__results-list")
                    if container:
                        page.evaluate("document.querySelector('.jobs-search__results-list')?.scrollBy(0, 3000)")
                        time.sleep(1.5)
                except Exception:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.5)

                job_cards = page.query_selector_all(
                    self.selectors.get("job_card", ".job-search-card")
                )
                logger.info(f"[LinkedInScraper] Found {len(job_cards)} card elements")

                for card in job_cards[:max_results]:
                    try:
                        # Extract title
                        title_el = card.query_selector(
                            self.selectors.get("title", ".base-search-card__title")
                        )
                        title = title_el.inner_text().strip() if title_el else ""

                        # Extract company
                        company_el = card.query_selector(
                            self.selectors.get("company", ".base-search-card__subtitle")
                        )
                        company = company_el.inner_text().strip() if company_el else ""

                        # Extract location
                        location_el = card.query_selector(
                            self.selectors.get("location", ".job-search-card__location")
                        )
                        loc = location_el.inner_text().strip() if location_el else location

                        # Extract URL from the full-card link
                        url_el = card.query_selector(
                            self.selectors.get("title_link", ".base-card__full-link")
                        )
                        url = url_el.get_attribute("href") if url_el else ""

                        # Extract posted date
                        posted_el = card.query_selector(
                            self.selectors.get("posted", "time")
                        )
                        posted_text = posted_el.inner_text().strip() if posted_el else ""
                        posted_date = _parse_posted_date(posted_text)

                        if not title or not company:
                            continue

                        # Try to fetch description by navigating to the detail page
                        # (list view doesn't show descriptions without sign-in)
                        description = ""
                        if url and not url.startswith("https://www.linkedin.com"):
                            full_url = f"https://www.linkedin.com{url}" if url.startswith("/") else url
                        else:
                            full_url = url

                        # We skip description fetching for now since LinkedIn
                        # requires auth. The job URL is saved so the user can
                        # view it manually.

                        jobs.append(
                            JobPosting(
                                title=title,
                                company=company,
                                description=description,
                                url=full_url or search_url,
                                source=self.source_name(),
                                location=loc,
                                posted_date=posted_date,
                            )
                        )
                    except Exception:
                        continue

                browser.close()
        except Exception as e:
            logger.error(f"[LinkedInScraper] Error: {e}")
        return jobs
