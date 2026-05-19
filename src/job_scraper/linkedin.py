"""LinkedIn job scraper using Playwright."""

import random
import time

from playwright.sync_api import sync_playwright

from config import SCRAPER_DELAY, SCRAPER_TIMEOUT, USER_AGENT
from src.utils.logging import get_logger

from .base import BaseScraper, JobPosting, with_retry

logger = get_logger(__name__)

class LinkedInScraper(BaseScraper):
    def source_name(self) -> str:
        return "linkedin"

    @with_retry(max_retries=3)
    def search(self, query: str, location: str = "", max_results: int = 25) -> list[JobPosting]:
        jobs = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()

                search_url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={query.replace(' ', '%20')}"
                    f"&location={location.replace(' ', '%20')}"
                )
                page.goto(search_url, timeout=SCRAPER_TIMEOUT)
                time.sleep(random.uniform(*SCRAPER_DELAY))

                # Scroll to load more results
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(random.uniform(1, 2))

                job_cards = page.query_selector_all(self.selectors.get("job_card", ".job-card-container"))
                for card in job_cards[:max_results]:
                    try:
                        title_el = card.query_selector(self.selectors.get("title", ".job-card-list__title"))
                        company_el = card.query_selector(self.selectors.get("company", ".job-card-container__company-name"))
                        location_el = card.query_selector(self.selectors.get("location", ".job-card-container__metadata-item"))
                        url_el = card.query_selector(self.selectors.get("title_link", "a"))

                        title = title_el.inner_text().strip() if title_el else ""
                        company = company_el.inner_text().strip() if company_el else ""
                        loc = location_el.inner_text().strip() if location_el else location
                        url = url_el.get_attribute("href") if url_el else ""

                        # Click card to load description
                        if card:
                            card.click()
                            time.sleep(1)
                            desc_el = page.query_selector(self.selectors.get("description", ".show-more-less-html__markup"))
                            desc = desc_el.inner_text().strip() if desc_el else ""

                        if title and company:
                            jobs.append(JobPosting(
                                title=title,
                                company=company,
                                description=desc,
                                url=url or search_url,
                                source=self.source_name(),
                                location=loc,
                            ))
                    except Exception:
                        continue

                browser.close()
        except Exception as e:
            logger.error(f"[LinkedInScraper] Error: {e}")
        return jobs
