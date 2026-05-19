"""Indeed job scraper."""

import time
import random
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from config import SCRAPER_TIMEOUT, SCRAPER_DELAY, USER_AGENT
from .base import BaseScraper, JobPosting, SelectorLoader, with_retry
from src.utils.logging import get_logger
logger = get_logger(__name__)

class IndeedScraper(BaseScraper):
    def source_name(self) -> str:
        return "indeed"

    @with_retry(max_retries=3)
    def search(self, query: str, location: str = "", max_results: int = 25) -> list[JobPosting]:
        jobs = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()

                url = (
                    f"https://www.indeed.com/jobs?"
                    f"q={quote(query)}&l={quote(location)}"
                )
                page.goto(url, timeout=SCRAPER_TIMEOUT)
                time.sleep(random.uniform(*SCRAPER_DELAY))

                cards = page.query_selector_all(self.selectors.get("job_card", ".job_seen_beacon"))
                for card in cards[:max_results]:
                    try:
                        title_el = card.query_selector(self.selectors.get("title", "h2.jobTitle a"))
                        company_el = card.query_selector(self.selectors.get("company", "[data-testid='companyName']"))
                        location_el = card.query_selector(self.selectors.get("location", "[data-testid='text-location']"))
                        salary_el = card.query_selector(self.selectors.get("salary", "[data-testid='attribute_snippet_testid']"))
                        desc_el = card.query_selector(self.selectors.get("description", ".job-snippet"))

                        title = title_el.get_attribute("title") or title_el.inner_text().strip() if title_el else ""
                        href = title_el.get_attribute("href") if title_el else ""
                        company = company_el.inner_text().strip() if company_el else ""
                        loc = location_el.inner_text().strip() if location_el else location
                        salary = salary_el.inner_text().strip() if salary_el else None
                        desc = desc_el.inner_text().strip() if desc_el else ""

                        if title and company:
                            jobs.append(JobPosting(
                                title=title,
                                company=company,
                                description=desc,
                                url=f"https://www.indeed.com{href}" if href else url,
                                source=self.source_name(),
                                location=loc,
                                salary=salary,
                            ))
                    except Exception:
                        continue

                browser.close()
        except Exception as e:
            logger.error(f"[IndeedScraper] Error: {e}")
        return jobs
