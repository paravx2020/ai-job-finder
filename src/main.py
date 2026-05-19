#!/usr/bin/env python3
"""JobFinder — CLI entry point."""

import json
from pathlib import Path

import click

from config import AI_MODEL, APP_NAME, APP_VERSION, CV_UPLOAD_DIR, DATA_DIR, EMAIL_SENDER
from src.auto_applier.applier import apply_to_job
from src.cv_processor import improver as cv_improver
from src.cv_processor import parser as cv_parser
from src.cv_processor import scorer as cv_scorer
from src.database import (
    Application,
    CVImprovementLog,
    JobPosting,
    User,
    UserProfile,
    find_job_by_url,
    get_session,
    init_db,
)
from src.notification import (
    notify_application_status,
    print_cv_score,
    print_header,
    print_improvement_diff,
    print_job_results,
    status_spinner,
)
from src.utils.exporter import build_analyze_export, build_search_export, export_results


@click.group()
@click.version_option(version=APP_VERSION, prog_name=APP_NAME)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--db", "db_path", type=click.Path(), default=None, help="Custom database path")
def cli(verbose: bool, quiet: bool, db_path: str | None):
    """JobFinder — AI-powered CV improvement and job matching."""
    from src.utils.logging import setup_logging

    setup_logging(verbose=verbose, quiet=quiet)
    if db_path:
        from config import settings

        settings.DB_PATH = db_path
    init_db()


@cli.command()
@click.argument("cv_path", type=click.Path(exists=True))
@click.option("--domain", default="software engineering", help="Target domain for improvements")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "pdf"]),
    default="text",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Write results to file")
@click.option("--user", "user_email", default=None, help="User email (creates profile if new)")
def analyze(
    cv_path: str, domain: str, output_format: str, output: str | None, user_email: str | None
):
    """Parse, score, and improve a CV file."""
    path = Path(cv_path)

    # Resolve user profile
    session = get_session()
    user_profile = None
    if user_email:
        user_profile = session.query(UserProfile).filter_by(email=user_email).first()
        if not user_profile:
            user_profile = UserProfile(
                email=user_email,
                name=user_email.split("@")[0],
                default_domain=domain,
            )
            session.add(user_profile)
            session.commit()
        # Use profile's domain if not explicitly set
        if domain == "software engineering" and user_profile.default_domain:
            domain = user_profile.default_domain

    with status_spinner("Parsing CV..."):
        parsed = cv_parser.parse_cv(path)
    click.echo(f"  File: {path.name}")
    click.echo(f"  Sections: {', '.join(parsed.sections.keys())}")
    click.echo(f"  Skills found: {len(parsed.skills)}")
    click.echo(f"  Word count: {parsed.word_count}")

    print_header("Scoring CV")
    with status_spinner("Scoring CV..."):
        score_data = cv_scorer.score_cv(parsed)
    print_cv_score(score_data)

    print_header("Improving CV")
    with status_spinner("Improving CV with AI..."):
        improvement = cv_improver.improve_cv(parsed, domain=domain)
    changes = improvement.changes
    if changes:
        print_improvement_diff(changes)
        improved = improvement.improved_sections
        for section, text in improved.items():
            click.echo(f"\n[Improved {section}]:")
            click.echo(f"  {text[:300]}...")
    else:
        click.echo("  No improvements suggested.")

    # Save to DB
    session = get_session()
    user_name = user_profile.name if user_profile else path.stem
    user_email_val = user_profile.email if user_profile else ""
    user = User(
        name=user_name, email=user_email_val, raw_cv_path=str(path), parsed_cv=parsed.model_dump()
    )
    session.add(user)
    for c in changes:
        section = c.section
        orig = parsed.sections.get(section, "")
        new_text = improvement.improved_sections.get(section, "")
        log = CVImprovementLog(
            user_id=user.id or 1,
            section=section,
            original_text=orig[:1000],
            improved_text=new_text[:1000],
            model_used=AI_MODEL,
        )
        session.add(log)
    session.commit()
    click.echo(f"\n[green]User saved with ID: {user.id}[/green]")

    # Handle export
    if output_format == "json" or (output and str(output).endswith(".json")):
        export_data = build_analyze_export(
            parsed.model_dump(), score_data.model_dump(), improvement.model_dump()
        )
        export_path = output or f"{path.stem}_analysis.json"
        export_results(export_data, export_path, title="CV Analysis Report")
        click.echo(f"[green]Report exported to {export_path}[/green]")
    elif output_format == "pdf" or (output and str(output).endswith(".pdf")):
        export_data = build_analyze_export(
            parsed.model_dump(), score_data.model_dump(), improvement.model_dump()
        )
        export_path = output or f"{path.stem}_analysis.pdf"
        export_results(export_data, export_path, title="CV Analysis Report")
        click.echo(f"[green]Report exported to {export_path}[/green]")
    elif output:
        # Plain text export
        with open(output, "w") as f:
            f.write("JobFinder CV Analysis\n")
            f.write(f"File: {path.name}\n")
            f.write(f"Domain: {domain}\n\n")
            f.write(f"Sections: {', '.join(parsed.sections.keys())}\n")
            f.write(f"Skills ({len(parsed.skills)}): {', '.join(parsed.skills)}\n")
            f.write(f"Word count: {parsed.word_count}\n\n")
            f.write(f"Overall score: {score_data.overall:.2f}\n")
            for s in score_data.suggestions:
                f.write(f"  - {s}\n")
        click.echo(f"Results written to {output}")


@cli.command()
@click.argument("cv_path", type=click.Path(exists=True))
@click.option("--query", default=None, help="Job search query (default: from CV skills)")
@click.option("--location", default="", help="Job location filter")
@click.option("--top-k", default=5, help="Number of top matches to show")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "pdf"]),
    default="text",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Write results to file")
@click.option("--user", "user_email", default=None, help="User email (creates profile if new)")
def search(
    cv_path: str,
    query: str,
    location: str,
    top_k: int,
    output_format: str,
    output: str | None,
    user_email: str | None,
):
    """Parse CV and find matching jobs."""
    path = Path(cv_path)

    # Resolve user profile
    session = get_session()
    user_profile = None
    if user_email:
        user_profile = session.query(UserProfile).filter_by(email=user_email).first()
        if not user_profile:
            user_profile = UserProfile(
                email=user_email,
                name=user_email.split("@")[0],
            )
            session.add(user_profile)
            session.commit()
        # Use profile's location if not explicitly set
        if not location and user_profile.default_location:
            location = user_profile.default_location

    with status_spinner("Parsing CV..."):
        parsed = cv_parser.parse_cv(path)

    # Auto-derive query from CV skills
    if not query:
        skills = parsed.skills
        query = " ".join(skills[:5]) if skills else "software engineer"
        click.echo(f"  Auto-query from skills: {query}")

    print_header(f"Searching Jobs: {query}")
    from src.job_scraper import engine as job_scraper_engine

    jobs = job_scraper_engine.search_all(query, location=location, max_per_source=25)
    click.echo(f"  Found {len(jobs)} unique jobs")

    if not jobs:
        click.echo("  No jobs found. Try a different query or location.")
        return

    print_header("Matching Jobs to CV")
    with status_spinner("Matching jobs to CV..."):
        from src.matcher import engine as matcher_engine

        matches = matcher_engine.match_jobs(parsed, jobs, top_k=top_k)
    click.echo(f"  Top {len(matches)} matches:")

    if not matches:
        click.echo("  No strong matches above threshold. Try broadening your search.")
        return

    print_job_results(matches)

    # Save matches to DB
    session = get_session()
    user = session.query(User).filter_by(raw_cv_path=str(path)).first()
    if not user:
        user = User(name=path.stem, email="", raw_cv_path=str(path), parsed_cv=parsed.model_dump())
        session.add(user)
        session.flush()

    for m in matches:
        job_data = m["job"]
        job_url = job_data.get("url", "")
        job = find_job_by_url(session, job_url)
        if not job:
            job = JobPosting(
                source=job_data.get("source", "web"),
                title=job_data["title"],
                company=job_data["company"],
                description="",
                url=job_url,
                salary=job_data.get("salary"),
                location=job_data.get("location"),
            )
            session.add(job)
            session.flush()
        app = Application(
            user_id=user.id,
            job_id=job.id,
            match_score=m["match_score"],
            match_reason=m.get("reason", ""),
            status="pending",
        )
        session.add(app)
    session.commit()

    # Save to file for the apply command
    matches_file = DATA_DIR / "latest_matches.json"
    with open(matches_file, "w") as f:
        json.dump(matches, f, indent=2)

    click.echo("\n  Matches saved. Run [bold]ai-job-finder apply[/bold] to submit applications.")

    # Handle export
    if output_format == "json" or (output and str(output).endswith(".json")):
        export_data = build_search_export(matches, query=query, location=location)
        export_path = output or f"{path.stem}_matches.json"
        export_results(export_data, export_path, title="Job Search Results")
        click.echo(f"[green]Report exported to {export_path}[/green]")
    elif output_format == "pdf" or (output and str(output).endswith(".pdf")):
        export_data = build_search_export(matches, query=query, location=location)
        export_path = output or f"{path.stem}_matches.pdf"
        export_results(export_data, export_path, title="Job Search Results")
        click.echo(f"[green]Report exported to {export_path}[/green]")
    elif output:
        with open(output, "w") as f:
            f.write("JobFinder Search Results\n")
            f.write(f"Query: {query}\n")
            f.write(f"Location: {location}\n")
            f.write(f"Matches: {len(matches)}\n\n")
            for i, m in enumerate(matches, 1):
                job = m["job"]
                f.write(f"{i}. {job['title']} @ {job['company']}\n")
                f.write(f"   Match: {m['match_percentage']} | URL: {job['url']}\n")
                f.write(f"   Reason: {m.get('reason', '')}\n\n")
        click.echo(f"Results written to {output}")


@cli.command()
@click.option("--index", type=int, default=None, help="Apply to a specific match by number")
@click.option("--all", "apply_all", is_flag=True, help="Apply to all matches")
@click.option("--cv", "cv_path", type=click.Path(exists=True), default=None, help="Path to CV file")
@click.option("--cover-letter", default="", help="Cover letter text")
@click.option("--user", "user_email", default=None, help="User email for application")
def apply(index: int, apply_all: bool, cv_path: str, cover_letter: str, user_email: str | None):
    """Apply to matched jobs."""

    matches_file = DATA_DIR / "latest_matches.json"
    if not matches_file.exists():
        click.echo("No matches found. Run 'ai-job-finder search' first.")
        return

    with open(matches_file) as f:
        matches = json.load(f)

    if not matches:
        click.echo("No saved matches.")
        return

    if index:
        matches = [matches[index - 1]]
    elif not apply_all:
        matches = [matches[0]]

    if not cv_path:
        cv_files = list(CV_UPLOAD_DIR.glob("*"))
        if not cv_files:
            click.echo("No CV found. Provide --cv path.")
            return
        cv_path = str(cv_files[0])

    session = get_session()
    user_profile = None
    if user_email:
        user_profile = session.query(UserProfile).filter_by(email=user_email).first()

    for m in matches:
        job = m["job"]
        print_header(f"Applying to: {job['title']} @ {job['company']}")

        user_name = user_profile.name if user_profile else "User"
        user_email_val = user_profile.email if user_profile else EMAIL_SENDER
        result = apply_to_job(
            job_url=job["url"],
            user_data={"name": user_name, "email": user_email_val, "company": job["company"]},
            resume_path=cv_path,
            cover_letter=cover_letter,
        )

        status = "submitted" if result["success"] else "failed"
        error = result.get("error", "")

        # Update DB
        app = (
            session.query(Application).join(JobPosting).filter(JobPosting.url == job["url"]).first()
        )
        if app:
            app.status = status
            app.applied_at = __import__("datetime").datetime.utcnow()
            app.response = error
            session.commit()

        click.echo(
            f"  Result: {'[green]Submitted[/green]' if result['success'] else f'[red]Failed: {error}[/red]'}"
        )

        if result["success"]:
            notify_application_status(job["title"], job["company"], status)

    session.close()


@cli.command("list")
@click.option("--status", default=None, help="Filter by status (pending, submitted, failed)")
@click.option("--limit", default=20, help="Maximum number of results to show")
def list_applications(status: str | None, limit: int):
    """List saved job applications."""
    from src.notification import print_header

    session = get_session()
    query = session.query(Application).join(JobPosting)
    if status:
        query = query.filter(Application.status == status)
    query = query.order_by(Application.created_at.desc()).limit(limit)
    applications = query.all()

    if not applications:
        click.echo("No applications found.")
        return

    print_header(f"Applications ({len(applications)})")
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Status")
    table.add_column("Score")
    table.add_column("Date")

    for i, app in enumerate(applications, 1):
        status_color = {
            "pending": "yellow",
            "submitted": "green",
            "failed": "red",
            "interview": "cyan",
        }.get(app.status, "white")
        date_str = app.created_at.strftime("%Y-%m-%d") if app.created_at else "N/A"
        table.add_row(
            str(i),
            app.job.title[:40] if app.job else "Unknown",
            app.job.company[:25] if app.job else "Unknown",
            f"[{status_color}]{app.status}[/{status_color}]",
            f"{app.match_score:.2f}" if app.match_score else "N/A",
            date_str,
        )
    console.print(table)
    session.close()


@cli.command()
def stats():
    """Show summary statistics."""
    from rich.console import Console
    from rich.table import Table

    from src.notification import print_header

    console = Console()

    session = get_session()
    total_jobs = session.query(JobPosting).count()
    total_apps = session.query(Application).count()
    pending = session.query(Application).filter_by(status="pending").count()
    submitted = session.query(Application).filter_by(status="submitted").count()
    failed = session.query(Application).filter_by(status="failed").count()

    # Average match score
    avg_score = (
        session.query(Application.match_score).filter(Application.match_score.isnot(None)).first()
    )
    avg_score_val = avg_score[0] if avg_score and avg_score[0] else 0

    # Sources breakdown
    sources = (
        session.query(JobPosting.source, __import__("sqlalchemy").func.count(JobPosting.id))
        .group_by(JobPosting.source)
        .all()
    )

    print_header("Statistics")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Total jobs in database", str(total_jobs))
    table.add_row("Total applications", str(total_apps))
    table.add_row("Pending applications", str(pending))
    table.add_row("Submitted applications", str(submitted))
    table.add_row("Failed applications", str(failed))
    table.add_row("Average match score", f"{avg_score_val:.2f}" if avg_score_val else "N/A")
    console.print(table)

    if sources:
        print_header("Jobs by Source")
        source_table = Table(show_header=True, header_style="bold magenta")
        source_table.add_column("Source")
        source_table.add_column("Count")
        for source, count in sources:
            source_table.add_row(source or "unknown", str(count))
        console.print(source_table)

    session.close()


@cli.command()
@click.argument("email", required=False)
@click.option("--name", default=None, help="User's full name")
@click.option("--phone", default=None, help="User's phone number")
@click.option("--domain", default=None, help="Default job domain")
@click.option("--location", default=None, help="Default job location")
def profile(
    email: str | None, name: str | None, phone: str | None, domain: str | None, location: str | None
):
    """Manage user profiles.

    Without arguments, shows the current profile.
    With an email, creates or updates a profile.
    """
    session = get_session()

    if not email:
        # Show existing profiles
        profiles = session.query(UserProfile).all()
        if not profiles:
            click.echo(
                "No user profiles found. Create one with: ai-job-finder profile you@example.com"
            )
        else:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Email")
            table.add_column("Name")
            table.add_column("Domain")
            table.add_column("Location")
            table.add_column("Created")
            for p in profiles:
                created = p.created_at.strftime("%Y-%m-%d") if p.created_at else "N/A"
                table.add_row(
                    p.email,
                    p.name or "—",
                    p.default_domain or "—",
                    p.default_location or "—",
                    created,
                )
            console.print(table)
        session.close()
        return

    # Create or update profile
    existing = session.query(UserProfile).filter_by(email=email).first()
    if existing:
        if name:
            existing.name = name
        if phone:
            existing.phone = phone
        if domain:
            existing.default_domain = domain
        if location:
            existing.default_location = location
        click.echo(f"[green]Updated profile: {email}[/green]")
    else:
        new_profile = UserProfile(
            email=email,
            name=name or email.split("@")[0],
            phone=phone,
            default_domain=domain or "software engineering",
            default_location=location,
        )
        session.add(new_profile)
        click.echo(f"[green]Created profile: {email}[/green]")

    session.commit()
    session.close()


if __name__ == "__main__":
    cli()
