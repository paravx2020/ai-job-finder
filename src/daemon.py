"""Autonomous daemon loop — runs the full pipeline unattended.

Usage:
    python -m src.daemon                # Run forever (sleeps DAEMON_SLEEP_HOURS)
    python -m src.daemon --once         # Single pipeline run (good for cron)
    python -m src.daemon --once --dry-run  # Preview without submitting
"""

import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    AUTO_APPLY_THRESHOLD,
    COMPANY_RESEARCH_ENABLED,
    CV_UPLOAD_DIR,
    DAEMON_SLEEP_HOURS,
    DATA_DIR,
    DRY_RUN,
    EMAIL_DAILY_SUMMARY,
    MAX_APPLICATIONS_PER_RUN,
)
from src.database import (
    Application,
    ApplicationResult,
    CompanyResearch,
    JobPosting,
    User,
    get_session,
    init_db,
    session_scope,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ── Pipeline Steps ──────────────────────────────────────────────────────────


def _find_latest_cv() -> Path | None:
    """Return the most recently analyzed CV from data/cvs/."""
    cvs = sorted(CV_UPLOAD_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for cv in cvs:
        if cv.suffix.lower() in (".pdf", ".docx", ".doc", ".txt"):
            return cv
    return None


def _load_matches(parsed_cv, session, dry_run: bool = False) -> list[dict]:
    """Search for jobs and run matcher. Returns list of match dicts."""
    from src.job_scraper import engine as job_scraper_engine
    from src.matcher import engine as matcher_engine

    skills = parsed_cv.skills
    query = " ".join(skills[:5]) if skills else "software engineer"

    logger.info(f"Searching jobs for query: {query}")
    source_jobs = job_scraper_engine.search_all(query, location="", max_per_source=25)
    logger.info(f"Found {len(source_jobs)} jobs from scrapers")

    if not source_jobs:
        return []

    # Deduplicate by URL (skip already-seen postings)
    existing_urls = {j.url for j in session.query(JobPosting.url).filter(JobPosting.url.in_([s.url for s in source_jobs if s.url])).all() if j.url}
    new_jobs = [j for j in source_jobs if j.url and j.url not in existing_urls]

    if not new_jobs:
        logger.info("No new jobs found (all previously seen)")
        return []

    logger.info(f"{len(new_jobs)} new jobs to match")
    matches = matcher_engine.match_jobs(parsed_cv, new_jobs, top_k=MAX_APPLICATIONS_PER_RUN, threshold=AUTO_APPLY_THRESHOLD)
    return matches


def _research_company(job_title: str, company_name: str, dry_run: bool = False) -> dict:
    """Gather intelligence about a company. Returns a research dict."""
    if dry_run:
        return {
            "summary_brief": f"[DRY RUN] Would research {company_name} for {job_title}.",
            "sources": [],
            "red_flags": [],
        }

    if not COMPANY_RESEARCH_ENABLED:
        return {"summary_brief": "", "sources": [], "red_flags": []}

    try:
        from src.company_research import research_company

        return research_company(company_name, job_title)
    except ImportError:
        logger.warning("Company research module not available — skipping")
        return {"summary_brief": "", "sources": [], "red_flags": []}
    except Exception as e:
        logger.warning(f"Company research failed for {company_name}: {e}")
        return {"summary_brief": f"Research unavailable for {company_name}.", "sources": [], "red_flags": []}


def _tailor_cv(parsed_cv, job_data: dict, dry_run: bool = False) -> tuple[str, str]:
    """Generate a tailored CV and cover letter for a specific job."""
    if dry_run:
        return (
            f"[DRY RUN] Would tailor CV for {job_data.get('title', 'Unknown')} @ {job_data.get('company', 'Unknown')}",
            f"[DRY RUN] Would generate cover letter for {job_data.get('title', 'Unknown')} @ {job_data.get('company', 'Unknown')}",
        )

    try:
        from src.tailoring import generate_tailored_cv, generate_cover_letter

        tailored_cv = generate_tailored_cv(parsed_cv, job_data)
        cover_letter = generate_cover_letter(parsed_cv, job_data)
        return tailored_cv, cover_letter
    except ImportError:
        logger.warning("Tailoring module not available — using generic CV")
        return "", ""
    except Exception as e:
        logger.warning(f"CV tailoring failed: {e}")
        return "", ""


def _red_flags_detected(research: dict) -> list[str]:
    """Check if company research revealed any red flags."""
    if not research:
        return []
    from config import COMPANY_RED_FLAG_KEYWORDS

    brief = research.get("summary_brief", "").lower()
    flags = [kw for kw in COMPANY_RED_FLAG_KEYWORDS if kw.strip().lower() in brief]
    return flags


def _apply_to_job(
    job_data: dict,
    user_data: dict,
    resume_path: str,
    cover_letter: str = "",
    dry_run: bool = False,
) -> dict:
    """Apply to a single job. Respects DRY_RUN."""
    if dry_run:
        logger.info(f"[DRY RUN] Would apply to {job_data.get('title')} @ {job_data.get('company')}")
        return {"success": True, "url": job_data.get("url", ""), "error": None, "dry_run": True}

    try:
        from src.auto_applier.applier import apply_to_job

        result = apply_to_job(
            job_url=job_data["url"],
            user_data=user_data,
            resume_path=resume_path,
            cover_letter=cover_letter,
            confirm=False,  # No confirmation in daemon mode
        )
        return result
    except Exception as e:
        return {"success": False, "url": job_data.get("url", ""), "error": str(e)}


# ── Main Daemon Loop ────────────────────────────────────────────────────────


def run_once(dry_run: bool = False) -> dict:
    """Execute a single pipeline run. Returns summary dict."""
    summary = {
        "jobs_found": 0,
        "jobs_applied": 0,
        "jobs_skipped": 0,
        "jobs_failed": 0,
        "callbacks": 0,
        "applied_companies": [],
        "skipped_reasons": [],
        "failed_details": [],
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
    }

    init_db()

    cv_path = _find_latest_cv()
    if not cv_path:
        logger.warning("No CV found in data/cvs/. Drop a CV to start.")
        return summary

    logger.info(f"Using CV: {cv_path}")

    # Parse CV
    from src.cv_processor import parser as cv_parser

    parsed = cv_parser.parse_cv(cv_path)

    # Search & match
    session = get_session()
    try:
        matches = _load_matches(parsed, session, dry_run=dry_run)
        summary["jobs_found"] = len(matches)
    finally:
        session.close()

    if not matches:
        logger.info("No strong matches found this cycle.")
        return summary

    # Process each match
    applied_count = 0

    for match in matches:
        if applied_count >= MAX_APPLICATIONS_PER_RUN:
            break

        job = match["job"]
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        match_score = match.get("match_score", 0)

        logger.info(f"Processing: {title} @ {company} (score: {match_score:.2f})")

        # Company research
        research = _research_company(title, company, dry_run=dry_run)
        red_flags = _red_flags_detected(research)
        if red_flags:
            summary["jobs_skipped"] += 1
            summary["skipped_reasons"].append(f"{title} @ {company}: red flags — {', '.join(red_flags)}")
            logger.warning(f"Skipping {company} — red flags: {red_flags}")
            continue

        # Tailor CV
        tailored_cv, cover_letter = _tailor_cv(parsed, job, dry_run=dry_run)
        if tailored_cv and not dry_run:
            tailored_dir = DATA_DIR / "tailored_cvs"
            tailored_dir.mkdir(parents=True, exist_ok=True)
            job_id = job.get("url", "unknown").replace("/", "_")[:100]
            tailored_path = tailored_dir / f"{job_id}_tailored.pdf"
            tailored_path.write_text(tailored_cv)

        # Apply
        user_name = "User"
        user_email = ""
        session = get_session()
        try:
            user = session.query(User).order_by(User.created_at.desc()).first()
            if user:
                user_name = user.name
                user_email = user.email
        finally:
            session.close()

        user_data = {"name": user_name, "email": user_email, "company": company}
        result = _apply_to_job(job, user_data, str(cv_path), cover_letter, dry_run=dry_run)

        if result.get("success"):
            summary["jobs_applied"] += 1
            summary["applied_companies"].append(f"{title} @ {company}")
            applied_count += 1

            # Save to DB
            _save_application(parsed, cv_path, job, match, tailored_cv, cover_letter, research, result, dry_run)
        else:
            summary["jobs_failed"] += 1
            err = result.get("error", "Unknown error")
            summary["failed_details"].append(f"{title} @ {company}: {err}")
            logger.error(f"Application failed: {title} @ {company} — {err}")

        # Rate limit delay
        if not dry_run and applied_count > 0:
            from config import APPLY_RATE_LIMIT_DELAY
            time.sleep(APPLY_RATE_LIMIT_DELAY)

    # Count callbacks (non-pending applications since last run)
    session = get_session()
    try:
        since_yesterday = datetime.utcnow() - timedelta(days=1)
        callbacks = session.query(Application).filter(
            Application.status.in_(["interview", "rejected", "offer"]),
            Application.applied_at >= since_yesterday,
        ).count()
        summary["callbacks"] = callbacks
    finally:
        session.close()

    return summary


def _save_application(parsed_cv, cv_path, job, match, tailored_cv, cover_letter, research, result, dry_run):
    """Persist application and research data to the database."""
    if dry_run:
        return

    from datetime import datetime as dt

    session = get_session()
    try:
        # Find or create job
        job_url = job.get("url", "")
        existing_job = session.query(JobPosting).filter_by(url=job_url).first()
        if not existing_job:
            existing_job = JobPosting(
                source=job.get("source", "daemon"),
                title=job.get("title", "Unknown"),
                company=job.get("company", "Unknown"),
                description=job.get("description", ""),
                url=job_url,
                salary=job.get("salary"),
                location=job.get("location"),
            )
            session.add(existing_job)
            session.flush()

        # Find user
        user = session.query(User).order_by(User.created_at.desc()).first()
        if not user:
            user = User(name="Daemon User", email="", raw_cv_path=str(cv_path), parsed_cv=parsed_cv.model_dump())
            session.add(user)
            session.flush()

        # Create Application
        app = Application(
            user_id=user.id,
            job_id=existing_job.id,
            match_score=match.get("match_score", 0),
            match_reason=match.get("reason", ""),
            status="submitted",
            applied_at=dt.utcnow(),
        )
        session.add(app)
        session.flush()

        # Save CompanyResearch
        research_id = None
        if research and research.get("summary_brief"):
            cr = CompanyResearch(
                job_id=existing_job.id,
                company_name=job.get("company", "Unknown"),
                summary_brief=research["summary_brief"],
                sources=research.get("sources", []),
                red_flags_found=research.get("red_flags", []),
            )
            session.add(cr)
            session.flush()
            research_id = cr.id

        # Create ApplicationResult
        app_result = ApplicationResult(
            application_id=app.id,
            job_id=existing_job.id,
            cv_used_path=str(cv_path),
            cover_letter_text=cover_letter,
            company_research_id=research_id,
            tailored_version_id=job.get("url", ""),
            status="submitted" if result.get("success") else "failed",
            error_message=result.get("error"),
        )
        session.add(app_result)

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save application to DB: {e}")
    finally:
        session.close()


def _send_daily_summary(summary: dict):
    """Send the daily summary via email."""
    if not EMAIL_DAILY_SUMMARY:
        return

    try:
        from src.notification.email_notifier import send_email

        applied = "\n".join(f"  - {c}" for c in summary.get("applied_companies", [])) or "  None"
        skipped = "\n".join(f"  - {r}" for r in summary.get("skipped_reasons", [])) or "  None"
        failed = "\n".join(f"  - {d}" for d in summary.get("failed_details", [])) or "  None"

        body = f"""JobFinder Daily Summary

Time: {summary.get('timestamp', 'N/A')}
Mode: {'DRY RUN' if summary.get('dry_run') else 'LIVE'}

Jobs Found:    {summary.get('jobs_found', 0)}
Jobs Applied:  {summary.get('jobs_applied', 0)}
Jobs Skipped:  {summary.get('jobs_skipped', 0)}
Jobs Failed:   {summary.get('jobs_failed', 0)}
Callbacks:     {summary.get('callbacks', 0)}

Applied:
{applied}

Skipped:
{skipped}

Failed:
{failed}
"""
        subject = f"[JobFinder] Daily Summary — {summary.get('jobs_applied', 0)} applications"
        if summary.get("dry_run"):
            subject = f"[JobFinder] DRY RUN Summary — {summary.get('jobs_found', 0)} job(s) found"

        send_email(subject, body)
    except Exception as e:
        logger.error(f"Failed to send daily summary email: {e}")


def run_forever(dry_run: bool = False):
    """Run the pipeline in a continuous loop."""
    logger.info(f"Daemon starting. Sleep interval: {DAEMON_SLEEP_HOURS}h. Dry run: {dry_run}")

    while True:
        logger.info("--- Daemon cycle start ---")
        try:
            summary = run_once(dry_run=dry_run)
            logger.info(f"Cycle complete: {summary['jobs_applied']} applied, {summary['jobs_found']} found")

            # Save report to file
            _save_report(summary)

            _send_daily_summary(summary)
        except Exception as e:
            logger.error(f"Daemon cycle crashed: {e}", exc_info=True)

        logger.info(f"Sleeping for {DAEMON_SLEEP_HOURS}h...")
        time.sleep(DAEMON_SLEEP_HOURS * 3600)


def _save_report(summary: dict):
    """Save the daily report to data/reports/."""
    import json

    reports_dir = DATA_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"report_{timestamp}.json"

    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Also save an HTML version if reporter exists
    try:
        from src.reporter import generate_html_report

        html = generate_html_report(summary)
        html_path = reports_dir / f"report_{timestamp}.html"
        html_path.write_text(html)
    except ImportError:
        pass


# ── CLI Entry Point ─────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="JobFinder Autonomous Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single pipeline cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without submitting applications")
    args = parser.parse_args()

    # Set up file logging
    log_dir = DATA_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    daemon_log = log_dir / "daemon.log"

    import logging

    file_handler = logging.FileHandler(str(daemon_log))
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)

    dry_run = args.dry_run or DRY_RUN

    if args.once:
        summary = run_once(dry_run=dry_run)
        _save_report(summary)
        _send_daily_summary(summary)

        logger.info("One-shot complete.")
        logger.info(f"  Jobs found:   {summary['jobs_found']}")
        logger.info(f"  Jobs applied: {summary['jobs_applied']}")
        logger.info(f"  Jobs skipped: {summary['jobs_skipped']}")
        logger.info(f"  Jobs failed:  {summary['jobs_failed']}")
        logger.info(f"  Callbacks:    {summary['callbacks']}")

        # Print to console too
        print(f"\n[JobFinder Daemon] {'DRY RUN' if dry_run else 'LIVE'} — Complete")
        print(f"  Jobs found:   {summary['jobs_found']}")
        print(f"  Jobs applied: {summary['jobs_applied']}")
        print(f"  Jobs skipped: {summary['jobs_skipped']}")
        print(f"  Jobs failed:  {summary['jobs_failed']}")
        print(f"  Callbacks:    {summary['callbacks']}")
        if summary["applied_companies"]:
            print("  Companies:")
            for c in summary["applied_companies"]:
                print(f"    - {c}")
    else:
        run_forever(dry_run=dry_run)


if __name__ == "__main__":
    main()
