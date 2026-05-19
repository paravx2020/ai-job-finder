"""Job scraping engine that runs multiple scrapers and deduplicates results."""

from datetime import datetime
from difflib import SequenceMatcher

from src.database import session_scope, find_job_by_url, JobPosting as DBJobPosting
from .base import JobPosting
from .linkedin import LinkedInScraper
from .indeed import IndeedScraper
from .glassdoor import GlassdoorScraper
from src.utils.logging import get_logger
logger = get_logger(__name__)

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(jobs: list[JobPosting], threshold: float = 0.75) -> list[JobPosting]:
    """Remove near-duplicate job postings."""
    unique = []
    for job in jobs:
        is_dup = False
        for existing in unique:
            title_sim = _similarity(job.title, existing.title)
            company_sim = _similarity(job.company, existing.company)
            if title_sim > threshold and company_sim > threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(job)
    return unique


def search_all(query: str, location: str = "", max_per_source: int = 25) -> list[JobPosting]:
    """Search all job sites and return deduplicated results."""
    from src.notification.console_notifier import create_progress

    scrapers = [LinkedInScraper(), IndeedScraper(), GlassdoorScraper()]
    all_jobs = []

    with create_progress() as progress:
        overall = progress.add_task("[cyan]Searching job sites...", total=len(scrapers))

        for scraper in scrapers:
            source_name = scraper.source_name()
            task = progress.add_task(f"  [yellow]{source_name}[/yellow]", total=1)
            try:
                results = scraper.search(query, location, max_results=max_per_source)
                all_jobs.extend(results)
                progress.update(task, description=f"  [green]{source_name}[/green] — {len(results)} jobs", completed=1)
            except Exception as e:
                progress.update(task, description=f"  [red]{source_name}[/red] — error: {e}", completed=1)
            progress.advance(overall)

    unique_jobs = deduplicate(all_jobs)

    # Persist to database with deduplication by URL
    new_count = 0
    updated_count = 0
    with session_scope() as session:
        for job in unique_jobs:
            existing = find_job_by_url(session, job.url)
            if existing:
                existing.last_scraped = datetime.utcnow()
                updated_count += 1
            else:
                db_job = DBJobPosting(
                    source=job.source,
                    title=job.title,
                    company=job.company,
                    description=job.description,
                    url=job.url,
                    salary=job.salary,
                    location=job.location,
                    posted_date=job.posted_date,
                    last_scraped=datetime.utcnow(),
                )
                session.add(db_job)
                new_count += 1

    logger.info(f"Total: {len(unique_jobs)} unique jobs ({new_count} new, {updated_count} updated)")
    return unique_jobs
