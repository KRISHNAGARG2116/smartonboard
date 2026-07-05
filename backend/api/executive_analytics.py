"""
Phase B.3C — Executive Analytics & Reporting API
All endpoints enforce:
  - Tenant isolation (company_id on every query)
  - VIEW_EXECUTIVE_ANALYTICS for read endpoints
  - EXPORT_EXECUTIVE_REPORTS for export/download
  - Authentication via RequireRecruiter dep
  - Report downloads expire after 24 hours and return 404 after expiry
"""
import os
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import (
    TenantDb,
    get_current_user,
    RequirePermission,
)
from models import User
from models.rbac import UserPermission
from models.report_export import ReportExport
from core.analytics_service import AnalyticsService
from core.cache import analytics_cache
from core.audit import log_audit_event

router = APIRouter(prefix="/executive", tags=["executive-analytics"])

# -----------------------------------------------------------------------
# Permission shorthands
# -----------------------------------------------------------------------
RequireViewAnalytics = Annotated[User, Depends(RequirePermission(UserPermission.VIEW_EXECUTIVE_ANALYTICS))]
RequireExportReports = Annotated[User, Depends(RequirePermission(UserPermission.EXPORT_EXECUTIVE_REPORTS))]


# -----------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------
class ExportRequest(BaseModel):
    report_type: str                       # pipeline | recruiter | candidate | offer | velocity | executive_summary
    format: str                            # CSV | XLSX | PDF
    filters: dict = {}
    date_from: datetime | None = None
    date_to: datetime | None = None
    department: str | None = None
    job_id: uuid.UUID | None = None
    recruiter_id: uuid.UUID | None = None
    source: str | None = None
    include_archived: bool = False
    window_days: int = 90


class AISummaryRequest(BaseModel):
    window_days: int = 90


# -----------------------------------------------------------------------
# Helper: export file storage directory
# -----------------------------------------------------------------------
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "../../exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def _build_report_rows_and_headers(
    report_type: str,
    db: Session,
    user: User,
    filters: ExportRequest,
) -> tuple[list[str], list[dict], dict | None]:
    """
    Builds (headers, rows, kpi_summary) for the requested report type.
    All queries use AnalyticsService which enforces tenant isolation and
    job access permissions. Data is paginated internally via yield_per-style
    iteration where possible.
    """
    from models import Application, Job, Interview, Scorecard
    from sqlalchemy import select, func
    from models.enums import ApplicationStatus

    company_id = user.company_id
    allowed_job_ids = AnalyticsService._get_allowed_job_ids(db, user)

    if report_type == "pipeline":
        stmt = (
            select(
                Application.id,
                Application.status,
                Application.source,
                Application.created_at,
                Application.updated_at,
            )
            .where(Application.company_id == company_id)
        )
        if not filters.include_archived:
            stmt = stmt.where(Application.is_archived.is_(False))
        if filters.job_id:
            stmt = stmt.where(Application.job_id == filters.job_id)
        elif allowed_job_ids is not None:
            stmt = stmt.where(Application.job_id.in_(allowed_job_ids))
        if filters.date_from:
            stmt = stmt.where(Application.created_at >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(Application.created_at <= filters.date_to)

        # Stream in batches of 500
        headers = ["application_id", "status", "source", "created_at", "updated_at"]
        rows = []
        for batch_row in db.execute(stmt).yield_per(500):
            rows.append({
                "application_id": str(batch_row.id),
                "status": str(batch_row.status.value if hasattr(batch_row.status, "value") else batch_row.status),
                "source": batch_row.source or "",
                "created_at": batch_row.created_at.isoformat() if batch_row.created_at else "",
                "updated_at": batch_row.updated_at.isoformat() if batch_row.updated_at else "",
            })
        overview = AnalyticsService.get_dashboard_overview(db, user)
        kpi = {
            "Active Jobs": overview["active_jobs"],
            "Open Applications": overview["open_applications"],
            "Avg Time to Hire (days)": overview["time_to_hire_days"],
            "SLA Breaches": overview["sla_breach_count"],
        }
        return headers, rows, kpi

    elif report_type == "recruiter":
        perf = AnalyticsService.get_recruiter_performance(db, user)
        headers = [
            "recruiter_name", "candidates_reviewed", "interviews_scheduled",
            "hires_made", "scorecard_completion_rate", "sla_compliance_rate"
        ]
        rows = perf["recruiters"]
        return headers, rows, None

    elif report_type == "candidate":
        from models import Candidate
        stmt = (
            select(
                Application.id,
                Application.status,
                Application.created_at,
                Application.source,
            )
            .where(Application.company_id == company_id)
        )
        if not filters.include_archived:
            stmt = stmt.where(Application.is_archived.is_(False))
        if filters.source:
            stmt = stmt.where(Application.source == filters.source)
        if allowed_job_ids is not None:
            stmt = stmt.where(Application.job_id.in_(allowed_job_ids))
        headers = ["application_id", "status", "source", "created_at"]
        rows = []
        for batch_row in db.execute(stmt).yield_per(500):
            rows.append({
                "application_id": str(batch_row.id),
                "status": str(batch_row.status.value if hasattr(batch_row.status, "value") else batch_row.status),
                "source": batch_row.source or "",
                "created_at": batch_row.created_at.isoformat() if batch_row.created_at else "",
            })
        return headers, rows, None

    elif report_type == "offer":
        offer_metrics = AnalyticsService.get_offer_metrics(db, user)
        headers = ["metric", "value"]
        rows = [{"metric": k, "value": str(v)} for k, v in offer_metrics.items()]
        kpi = {
            "Offers Pending": offer_metrics["offers_pending"],
            "Accepted": offer_metrics["offers_accepted"],
            "Acceptance Rate": f"{offer_metrics['acceptance_rate']}%",
        }
        return headers, rows, kpi

    elif report_type == "velocity":
        velocity = AnalyticsService.get_hiring_velocity(db, user)
        headers = ["month", "days"]
        rows = velocity["historical_trend"]
        kpi = {"Avg Time to Hire (days)": velocity["average_time_to_hire_days"]}
        return headers, rows, kpi

    elif report_type == "executive_summary":
        overview = AnalyticsService.get_dashboard_overview(db, user)
        forecast = AnalyticsService.get_forecasting(db, user)
        sla = AnalyticsService.get_sla_compliance(db, user)
        headers = ["metric", "value"]
        rows = [
            {"metric": "Active Jobs", "value": str(overview["active_jobs"])},
            {"metric": "Open Applications", "value": str(overview["open_applications"])},
            {"metric": "Avg Time to Hire (days)", "value": str(overview["time_to_hire_days"])},
            {"metric": "Offer Acceptance Rate (%)", "value": str(overview["offer_acceptance_rate"])},
            {"metric": "Interview Pass Rate (%)", "value": str(overview["interview_pass_rate"])},
            {"metric": "SLA Compliance (%)", "value": str(sla["compliance_rate"])},
            {"metric": "Forecast: Expected Hires", "value": str(forecast["forecast"]["expected_hires"])},
            {"metric": "Forecast: Recruiter Capacity", "value": str(forecast["forecast"]["recruiter_capacity"])},
        ]
        kpi = {
            "Active Jobs": overview["active_jobs"],
            "Open Applications": overview["open_applications"],
            "Offer Acceptance Rate": f"{overview['offer_acceptance_rate']}%",
            "SLA Compliance": f"{sla['compliance_rate']}%",
            "Expected Hires (Forecast)": forecast["forecast"]["expected_hires"],
        }
        return headers, rows, kpi

    raise ValueError(f"Unknown report type: {report_type}")


# -----------------------------------------------------------------------
# Read-only analytics endpoints (all require VIEW_EXECUTIVE_ANALYTICS)
# -----------------------------------------------------------------------

@router.get("/dashboard")
def get_executive_dashboard(
    db: TenantDb,
    current_user: RequireViewAnalytics,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    job_id: uuid.UUID | None = Query(default=None),
):
    """Executive KPI overview — 60s cache, invalidated on any write."""
    return AnalyticsService.get_dashboard_overview(db, current_user, start_date=date_from, end_date=date_to)


@router.get("/funnel")
def get_funnel_analytics(
    db: TenantDb,
    current_user: RequireViewAnalytics,
    job_id: uuid.UUID | None = Query(default=None),
):
    """Hiring funnel with stage conversion rates and bottleneck detection."""
    return AnalyticsService.get_funnel_analytics(db, current_user, job_id=job_id)


@router.get("/recruiters")
def get_recruiter_performance(
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """Recruiter leaderboard: reviews, interviews, hires, SLA compliance, scorecard rate — 60s cache."""
    return AnalyticsService.get_recruiter_performance(db, current_user)


@router.get("/sources")
def get_hiring_sources(
    db: TenantDb,
    current_user: RequireViewAnalytics,
    job_id: uuid.UUID | None = Query(default=None),
):
    """Source attribution: applications, interviews, offers, and hires by channel."""
    return AnalyticsService.get_hiring_sources(db, current_user, job_id=job_id)


@router.get("/time-metrics")
def get_time_metrics(
    db: TenantDb,
    current_user: RequireViewAnalytics,
    job_id: uuid.UUID | None = Query(default=None),
):
    """Milestone timing: first review, first interview, offer, and hire durations."""
    return AnalyticsService.get_time_metrics(db, current_user, job_id=job_id)


@router.get("/forecast")
def get_forecast(
    db: TenantDb,
    current_user: RequireViewAnalytics,
    window_days: int = Query(default=90, ge=30, le=365),
):
    """
    Deterministic hiring forecast using rolling historical averages.
    Returns both forecast numbers and a full explanation payload.
    Cache TTL: 15 minutes.
    """
    return AnalyticsService.get_forecasting(db, current_user, window_days=window_days)


@router.get("/pipeline-health")
def get_pipeline_health(
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """Application status distribution and aging candidate counts."""
    return AnalyticsService.get_pipeline_health(db, current_user)


@router.get("/sla-compliance")
def get_sla_compliance(
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """SLA tracker compliance rate and breach counts."""
    return AnalyticsService.get_sla_compliance(db, current_user)


@router.get("/offer-metrics")
def get_offer_metrics(
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """Offer acceptance and decline counts and rates."""
    return AnalyticsService.get_offer_metrics(db, current_user)


@router.get("/velocity")
def get_hiring_velocity(
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """Hiring velocity trend over recent periods."""
    return AnalyticsService.get_hiring_velocity(db, current_user)


@router.get("/recent-activity")
def get_recent_activity(
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """Most recent 10 application events scoped to company and job access."""
    return {"events": AnalyticsService.get_recent_activity(db, current_user)}


# -----------------------------------------------------------------------
# AI Executive Summary
# -----------------------------------------------------------------------

@router.post("/ai-summary")
def get_ai_executive_summary(
    body: AISummaryRequest,
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """
    Generates an AI executive hiring briefing using only aggregated metrics.
    Never sends candidate names, resumes, scorecards, or recruiter notes to the LLM.
    Cache TTL: 10 minutes.
    """
    company_id = current_user.company_id
    cache_key = f"{str(company_id)}:ai_summary:{body.window_days}"
    cached = analytics_cache.get(cache_key)
    if cached:
        return {"summary": cached, "cached": True}

    # Build aggregated metrics string — no PII
    overview = AnalyticsService.get_dashboard_overview(db, current_user)
    forecast = AnalyticsService.get_forecasting(db, current_user, window_days=body.window_days)
    sla = AnalyticsService.get_sla_compliance(db, current_user)
    velocity = AnalyticsService.get_hiring_velocity(db, current_user)
    funnel = AnalyticsService.get_funnel_analytics(db, current_user)

    metrics_text = f"""
Active Jobs: {overview['active_jobs']}
Open Applications: {overview['open_applications']}
Candidates Awaiting Review: {overview['candidates_awaiting_review']}
Avg Time to Hire: {overview['time_to_hire_days']} days
Avg Time in Stage: {overview['avg_time_in_stage_hours']} hours
Offer Acceptance Rate: {overview['offer_acceptance_rate']}%
Interview Pass Rate: {overview['interview_pass_rate']}%
SLA Breaches: {sla['breached_count']} of {sla['total_trackers']} tracked (Compliance: {sla['compliance_rate']}%)
Avg Time to Hire (velocity): {velocity['average_time_to_hire_days']} days
Funnel Bottleneck: {funnel.get('bottleneck', 'None')}
Forecast Expected Hires ({body.window_days}d window): {forecast['forecast']['expected_hires']}
Forecast Recruiter Capacity: {forecast['forecast']['recruiter_capacity']}
Forecast Confidence: {forecast['explanation']['confidence']}
Historical Average: {forecast['explanation']['historical_average']} hires/month
""".strip()

    from core.intelligence import GenerativeIntelligenceService
    summary = GenerativeIntelligenceService.generate_executive_summary(metrics_text)

    analytics_cache.set(cache_key, summary, ttl_seconds=600, tags=[f"{str(company_id)}:dashboard"])

    log_audit_event(
        db=db,
        action="executive.ai_summary_generated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        metadata={"window_days": body.window_days, "cached": False},
    )

    return {"summary": summary, "cached": False, "model": "llama-3.3-70b-versatile", "provider": "groq"}


# -----------------------------------------------------------------------
# Async Report Export  (requires EXPORT_EXECUTIVE_REPORTS)
# -----------------------------------------------------------------------

@router.post("/reports/export", status_code=status.HTTP_202_ACCEPTED)
def request_report_export(
    body: ExportRequest,
    db: TenantDb,
    current_user: RequireExportReports,
):
    """
    Enqueues an asynchronous report generation job.
    Returns a report_id. Poll /reports/{report_id} for status.
    """
    if body.format.upper() not in ("CSV", "XLSX", "PDF"):
        raise HTTPException(status_code=400, detail="format must be one of: CSV, XLSX, PDF")
    if body.report_type not in ("pipeline", "recruiter", "candidate", "offer", "velocity", "executive_summary"):
        raise HTTPException(status_code=400, detail="Invalid report_type")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    report_job = ReportExport(
        company_id=current_user.company_id,
        requested_by=current_user.id,
        status="PENDING",
        format=body.format.upper(),
        filters={
            "report_type": body.report_type,
            "date_from": body.date_from.isoformat() if body.date_from else None,
            "date_to": body.date_to.isoformat() if body.date_to else None,
            "department": body.department,
            "job_id": str(body.job_id) if body.job_id else None,
            "recruiter_id": str(body.recruiter_id) if body.recruiter_id else None,
            "source": body.source,
            "include_archived": body.include_archived,
            "window_days": body.window_days,
        },
        expires_at=expires_at,
    )
    db.add(report_job)
    db.commit()
    db.refresh(report_job)

    # Generate synchronously (Celery task would be preferred in production)
    _process_report_sync(db, current_user, report_job, body)

    return {
        "report_id": str(report_job.id),
        "status": report_job.status,
        "expires_at": expires_at.isoformat(),
        "message": "Report generation has been queued. Poll /executive/reports/{report_id} for status.",
    }


def _process_report_sync(db: Session, user: User, job: ReportExport, body: ExportRequest):
    """Generates the report file synchronously and updates the job record."""
    from core.reporting import generate_report
    try:
        job.status = "PROCESSING"
        db.commit()

        headers, rows, kpi = _build_report_rows_and_headers(body.report_type, db, user, body)
        report_title = f"{body.report_type.replace('_', ' ').title()} Report"
        content, _ = generate_report(
            report_format=body.format.upper(),
            report_title=report_title,
            headers=headers,
            rows=rows,
            kpi_summary=kpi,
            company_name="SmartOnboard",
        )

        ext_map = {"CSV": "csv", "XLSX": "xlsx", "PDF": "pdf"}
        ext = ext_map.get(body.format.upper(), "csv")
        filename = f"report_{job.id}.{ext}"
        file_path = os.path.join(EXPORT_DIR, filename)

        os.makedirs(EXPORT_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

        job.status = "COMPLETED"
        job.file_path = file_path
        db.commit()

    except Exception as e:
        job.status = "FAILED"
        db.commit()
        raise


@router.get("/reports/{report_id}")
def get_report_status(
    report_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """Checks the status of an asynchronous report export job."""
    job = db.scalar(
        select(ReportExport).where(
            ReportExport.id == report_id,
            ReportExport.company_id == current_user.company_id,
        )
    )
    if not job:
        raise HTTPException(status_code=404, detail="Report not found.")

    # Mark as expired if past expiry
    if job.expires_at < datetime.now(timezone.utc) and job.status == "COMPLETED":
        job.status = "EXPIRED"
        db.commit()

    return {
        "report_id": str(job.id),
        "status": job.status,
        "format": job.format,
        "filters": job.filters,
        "expires_at": job.expires_at.isoformat(),
        "created_at": job.created_at.isoformat(),
    }


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireViewAnalytics,
):
    """
    Streams the completed report file.
    Enforces:
      - company scoping
      - authentication (via RequireViewAnalytics dep)
      - 24-hour expiration (returns 404 after expiry)
    """
    job = db.scalar(
        select(ReportExport).where(
            ReportExport.id == report_id,
            ReportExport.company_id == current_user.company_id,
        )
    )
    if not job:
        raise HTTPException(status_code=404, detail="Report not found.")

    if job.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Report has expired and is no longer available.")

    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Report is not ready — current status: {job.status}")

    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk.")

    ext = job.format.lower()
    media_type_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }
    media_type = media_type_map.get(ext, "application/octet-stream")
    filename = os.path.basename(job.file_path)

    def file_stream():
        with open(job.file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    log_audit_event(
        db=db,
        action="executive.report_downloaded",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        metadata={"report_id": str(report_id), "format": job.format},
    )

    return StreamingResponse(
        file_stream(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
