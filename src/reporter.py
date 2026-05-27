"""Report generation — produces HTML and text summaries of daemon activity.

Used by the daemon to save post-run reports and by the CLI `report` command.
"""

from datetime import datetime
from pathlib import Path

from config import DATA_DIR
from src.utils.logging import get_logger

logger = get_logger(__name__)


def generate_text_report(summary: dict) -> str:
    """Generate a plain-text summary report.

    Args:
        summary: Dict from daemon.run_once() with keys:
            jobs_found, jobs_applied, jobs_skipped, jobs_failed,
            callbacks, applied_companies, skipped_reasons, failed_details,
            timestamp, dry_run

    Returns:
        Formatted text report
    """
    mode = "DRY RUN" if summary.get("dry_run") else "LIVE"
    lines = [
        "=" * 60,
        f"  JobFinder Report — {mode}",
        f"  {summary.get('timestamp', datetime.utcnow().isoformat())}",
        "=" * 60,
        "",
        f"  Jobs Found:    {summary.get('jobs_found', 0)}",
        f"  Jobs Applied:  {summary.get('jobs_applied', 0)}",
        f"  Jobs Skipped:  {summary.get('jobs_skipped', 0)}",
        f"  Jobs Failed:   {summary.get('jobs_failed', 0)}",
        f"  Callbacks:     {summary.get('callbacks', 0)}",
        "",
    ]

    applied = summary.get("applied_companies", [])
    if applied:
        lines.append("  Applied to:")
        for c in applied:
            lines.append(f"    ✓ {c}")
        lines.append("")

    skipped = summary.get("skipped_reasons", [])
    if skipped:
        lines.append("  Skipped:")
        for r in skipped:
            lines.append(f"    ✗ {r}")
        lines.append("")

    failed = summary.get("failed_details", [])
    if failed:
        lines.append("  Failed:")
        for d in failed:
            lines.append(f"    ⚠ {d}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def generate_html_report(summary: dict) -> str:
    """Generate an HTML summary report suitable for email or viewing in browser.

    Args:
        summary: Same dict as generate_text_report

    Returns:
        HTML string
    """
    mode = summary.get("dry_run", False)
    mode_label = "🚨 DRY RUN" if mode else "✅ LIVE"
    mode_class = "dry-run" if mode else "live"

    timestamp = summary.get("timestamp", datetime.utcnow().isoformat())
    jobs_found = summary.get("jobs_found", 0)
    jobs_applied = summary.get("jobs_applied", 0)
    jobs_skipped = summary.get("jobs_skipped", 0)
    jobs_failed = summary.get("jobs_failed", 0)
    callbacks = summary.get("callbacks", 0)

    applied_html = ""
    for c in summary.get("applied_companies", []):
        applied_html += f"<li>✓ {c}</li>\n"

    skipped_html = ""
    for r in summary.get("skipped_reasons", []):
        skipped_html += f"<li>✗ {r}</li>\n"

    failed_html = ""
    for d in summary.get("failed_details", []):
        failed_html += f"<li>⚠ {d}</li>\n"

    success_rate = round(jobs_applied / max(jobs_found, 1) * 100, 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobFinder Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
  .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
  .header .mode {{ font-size: 14px; opacity: 0.9; }}
  .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }}
  .stat {{ background: #f8fafc; padding: 16px; border-radius: 8px; text-align: center; }}
  .stat .number {{ font-size: 28px; font-weight: 700; color: #6366f1; }}
  .stat .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
  .section {{ margin-bottom: 20px; }}
  .section h3 {{ font-size: 16px; color: #475569; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 6px 0; font-size: 14px; border-bottom: 1px solid #f1f5f9; }}
  .success-rate {{ margin-bottom: 24px; padding: 12px; background: #ecfdf5; border-radius: 8px; color: #065f46; font-weight: 600; }}
  .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 JobFinder Report</h1>
  <div class="mode">{mode_label}</div>
  <div style="font-size:12px; opacity:0.7; margin-top:4px;">{timestamp}</div>
</div>

<div class="success-rate">
  📊 Success Rate: {success_rate}% ({jobs_applied}/{jobs_found} jobs)
</div>

<div class="stats">
  <div class="stat">
    <div class="number">{jobs_found}</div>
    <div class="label">Jobs Found</div>
  </div>
  <div class="stat">
    <div class="number">{jobs_applied}</div>
    <div class="label">Applied</div>
  </div>
  <div class="stat">
    <div class="number">{callbacks}</div>
    <div class="label">Callbacks</div>
  </div>
</div>

{_section("Applied", applied_html)}
{_section("Skipped", skipped_html)}
{_section("Failed", failed_html)}

<div class="footer">
  Generated by JobFinder • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
</div>
</body>
</html>"""


def _section(title: str, items_html: str) -> str:
    """Generate an HTML section if items exist."""
    if not items_html.strip():
        return ""
    return f"""<div class="section">
  <h3>{title}</h3>
  <ul>{items_html}</ul>
</div>"""


def save_report(summary: dict, output_dir: Path | None = None) -> Path:
    """Save a report as both HTML and JSON.

    Args:
        summary: Report summary dict
        output_dir: Optional output directory (defaults to data/reports/)

    Returns:
        Path to the saved HTML report
    """
    reports_dir = output_dir or (DATA_DIR / "reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # HTML report
    html = generate_html_report(summary)
    html_path = reports_dir / f"report_{timestamp}.html"
    html_path.write_text(html)

    # JSON report
    import json

    json_path = reports_dir / f"report_{timestamp}.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    # Also save latest as "latest.html" for quick viewing
    latest_path = reports_dir / "latest.html"
    latest_path.write_text(html)
    (reports_dir / "latest.json").write_text(json.dumps(summary, indent=2, default=str))

    logger.info(f"Report saved to {html_path}")
    return html_path
