"""Response tracking and application strategy optimization.

Tracks which CV versions and tailoring approaches get the best callback
rates and automatically prefers the top-performing strategy.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from config import FOLLOW_UP_GHOSTED_AFTER_DAYS, TRACK_OPTIMIZATION_ENABLED
from src.database import (
    Application,
    ApplicationResult,
    CompanyResearch,
    JobPosting,
    get_session,
    session_scope,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

VALID_STATUSES = {"submitted", "rejected", "interview", "ghosted", "offer", "failed"}


# ── Response Tracking ────────────────────────────────────────────────────────


def track_response(application_id: int, status: str) -> dict[str, Any]:
    """Update the status of a tracked application.

    Args:
        application_id: ID of the ApplicationResult or Application
        status: One of rejected, interview, ghosted, offer

    Returns:
        Dict with success and details
    """
    if status not in VALID_STATUSES:
        return {"success": False, "error": f"Invalid status: {status}. Valid: {VALID_STATUSES}"}

    with session_scope() as session:
        # Try ApplicationResult first (preferred for detailed tracking)
        result_entry = session.query(ApplicationResult).filter_by(id=application_id).first()
        if result_entry:
            result_entry.status = status
            result_entry.response_received_at = datetime.utcnow()

            # Also update parent Application if linked
            if result_entry.application_id:
                app = session.query(Application).filter_by(id=result_entry.application_id).first()
                if app:
                    app.status = status
                    app.applied_at = result_entry.response_received_at

            logger.info(f"Updated ApplicationResult {application_id} → {status}")
            return {"success": True, "id": application_id, "status": status, "type": "application_result"}

        # Fallback: try Application directly
        app = session.query(Application).filter_by(id=application_id).first()
        if app:
            app.status = status
            app.applied_at = datetime.utcnow()
            logger.info(f"Updated Application {application_id} → {status}")
            return {"success": True, "id": application_id, "status": status, "type": "application"}

    return {"success": False, "error": f"No application found with ID {application_id}"}


def auto_mark_ghosted() -> int:
    """Mark old applications as 'ghosted' if no response after threshold days.

    Returns:
        Number of applications marked as ghosted.
    """
    cutoff = datetime.utcnow() - timedelta(days=FOLLOW_UP_GHOSTED_AFTER_DAYS)

    with session_scope() as session:
        # Check ApplicationResult entries
        stale = (
            session.query(ApplicationResult)
            .filter(
                ApplicationResult.status == "submitted",
                ApplicationResult.applied_at <= cutoff,
            )
            .all()
        )

        count = 0
        for entry in stale:
            entry.status = "ghosted"
            count += 1

            # Update linked Application
            if entry.application_id:
                app = session.query(Application).filter_by(id=entry.application_id).first()
                if app and app.status == "submitted":
                    app.status = "ghosted"

        if count:
            logger.info(f"Auto-marked {count} applications as ghosted (no response in {FOLLOW_UP_GHOSTED_AFTER_DAYS}+ days)")

        return count


# ── Performance Analysis ─────────────────────────────────────────────────────


def analyze_performance(min_applications: int = 5) -> dict[str, Any]:
    """Analyze which CV strategies have the best callback rates.

    Args:
        min_applications: Minimum applications before analysis is meaningful

    Returns:
        Dict with performance breakdown and recommendations
    """
    if not TRACK_OPTIMIZATION_ENABLED:
        return {"enabled": False, "message": "Optimization tracking is disabled"}

    session = get_session()
    try:
        # Get all ApplicationResults with CV paths
        results = (
            session.query(ApplicationResult)
            .filter(ApplicationResult.status.in_(["submitted", "rejected", "interview", "ghosted", "offer"]))
            .all()
        )

        if len(results) < min_applications:
            return {
                "enabled": True,
                "total_applications": len(results),
                "message": f"Need at least {min_applications} applications for meaningful analysis (have {len(results)})",
            }

        # Group by CV path / tailoring approach
        cv_groups: dict[str, dict[str, Any]] = {}
        for r in results:
            key = r.cv_used_path or "unknown"
            if key not in cv_groups:
                cv_groups[key] = {"total": 0, "interview": 0, "rejected": 0, "ghosted": 0, "offer": 0, "submitted": 0}

            cv_groups[key]["total"] += 1
            status = r.status
            if status in cv_groups[key]:
                cv_groups[key][status] += 1

        # Calculate callback rates
        analysis = []
        for path, stats in cv_groups.items():
            total = stats["total"]
            callbacks = stats["interview"] + stats["offer"]
            callback_rate = callbacks / total if total > 0 else 0

            analysis.append({
                "cv_path": path,
                "total": total,
                "interviews": stats["interview"],
                "offers": stats["offer"],
                "rejected": stats["rejected"],
                "ghosted": stats["ghosted"],
                "submitted": stats["submitted"],
                "callback_rate": round(callback_rate, 3),
                "callback_percentage": f"{round(callback_rate * 100, 1)}%",
            })

        # Sort by callback rate descending
        analysis.sort(key=lambda x: x["callback_rate"], reverse=True)

        best = analysis[0] if analysis else None

        # Check for company research correlation
        with_research = (
            session.query(ApplicationResult)
            .filter(
                ApplicationResult.company_research_id.isnot(None),
                ApplicationResult.status.in_(["interview", "offer"]),
            )
            .count()
        )
        total_callbacks = sum(a["interviews"] + a["offers"] for a in analysis)

        research_impact = None
        if total_callbacks > 0:
            total_with_research = (
                session.query(ApplicationResult)
                .filter(ApplicationResult.company_research_id.isnot(None))
                .count()
            )
            research_impact = f"{with_research}/{total_callbacks} callbacks had company research ({round(with_research / max(total_callbacks, 1) * 100, 1)}%)"

        return {
            "enabled": True,
            "total_applications": len(results),
            "best_approach": best,
            "all_approaches": analysis,
            "research_impact": research_impact,
            "recommendation": (
                f"Best: {best['cv_path'][-50:]} at {best['callback_percentage']} callback rate"
                if best
                else "Insufficient data"
            ),
        }
    finally:
        session.close()


def get_best_cv_strategy() -> str | None:
    """Return the best-performing CV path, or None if insufficient data."""
    perf = analyze_performance(min_applications=10)
    best = perf.get("best_approach")
    if best and best["callback_rate"] > 0:
        return best["cv_path"]
    return None


# ── Ghosted Follow-up Suggestion ─────────────────────────────────────────────


def suggest_follow_ups() -> list[dict]:
    """Find ghosted applications that could use a follow-up email."""
    cutoff = datetime.utcnow() - timedelta(days=FOLLOW_UP_GHOSTED_AFTER_DAYS)

    session = get_session()
    try:
        ghosted = (
            session.query(ApplicationResult)
            .filter(
                ApplicationResult.status == "ghosted",
                ApplicationResult.applied_at <= cutoff,
            )
            .all()
        )

        suggestions = []
        for entry in ghosted:
            job = session.query(JobPosting).filter_by(id=entry.job_id).first()
            suggestions.append({
                "application_id": entry.id,
                "job_title": job.title if job else "Unknown",
                "company": job.company if job else "Unknown",
                "applied_at": entry.applied_at.isoformat() if entry.applied_at else "unknown",
                "days_since_applied": (datetime.utcnow() - entry.applied_at).days if entry.applied_at else 0,
            })

        return suggestions
    finally:
        session.close()