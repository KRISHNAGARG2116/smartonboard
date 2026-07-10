import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from api.deps import TenantDb, RequireRecruiter, has_job_access
from models import Application, Job, Candidate, StageDefinition
from models.sla import CandidateStageSLATracker
from core.redis_cache import cached

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class WidgetLayoutUpdate(BaseModel):
    widgets_layout: dict


def ensure_preferences_table_exists(db):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS recruiter_dashboard_preferences (
            id UUID PRIMARY KEY,
            company_id UUID NOT NULL,
            user_id UUID NOT NULL UNIQUE,
            widgets_layout JSONB NOT NULL DEFAULT '{}'::jsonb
        );
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_recruiter_dash_pref_user ON recruiter_dashboard_preferences(user_id);
    """))
    db.commit()


@router.get("/preferences")
def get_dashboard_preferences(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Returns the recruiter's dashboard widget preferences layout config.
    """
    ensure_preferences_table_exists(db)
    result = db.execute(
        text("SELECT widgets_layout FROM recruiter_dashboard_preferences WHERE user_id = :user_id"),
        {"user_id": current_user.id}
    ).fetchone()

    if not result:
        # Default layout preference
        return {
            "widgets_layout": {
                "sla_alerts": {"visible": True, "order": 1},
                "next_candidate": {"visible": True, "order": 2},
                "calendar_agenda": {"visible": True, "order": 3},
                "recent_notifications": {"visible": True, "order": 4}
            }
        }

    return {"widgets_layout": result[0]}


@router.put("/preferences")
def update_dashboard_preferences(
    body: WidgetLayoutUpdate,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Updates or inserts the recruiter's customized layout order/visibility settings.
    """
    ensure_preferences_table_exists(db)
    result = db.execute(
        text("SELECT id FROM recruiter_dashboard_preferences WHERE user_id = :user_id"),
        {"user_id": current_user.id}
    ).fetchone()

    import json
    widgets_json = json.dumps(body.widgets_layout)

    if result:
        db.execute(
            text("UPDATE recruiter_dashboard_preferences SET widgets_layout = :layout WHERE user_id = :user_id"),
            {"layout": widgets_json, "user_id": current_user.id}
        )
    else:
        new_id = uuid.uuid4()
        db.execute(
            text("INSERT INTO recruiter_dashboard_preferences (id, company_id, user_id, widgets_layout) VALUES (:id, :company_id, :user_id, :layout)"),
            {
                "id": new_id,
                "company_id": current_user.company_id,
                "user_id": current_user.id,
                "layout": widgets_json
            }
        )
    db.commit()
    return {"status": "success", "widgets_layout": body.widgets_layout}


@router.get("/widgets")
@cached(namespace="dashboard_widgets", ttl=120)
def get_dashboard_widgets_data(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Retrieves aggregated dashboard data for all four custom widgets:
    SLA alerts list, quick review next candidate action, calendar agenda list, and recent notification center.
    """
    # 1. SLA alerts list
    trackers = db.scalars(
        select(CandidateStageSLATracker)
        .join(Application, CandidateStageSLATracker.application_id == Application.id)
        .where(
            CandidateStageSLATracker.company_id == current_user.company_id,
            CandidateStageSLATracker.status.in_(["active", "breached"])
        )
    ).all()

    sla_alerts = []
    for t in trackers:
        app = db.get(Application, t.application_id)
        if app and has_job_access(db, current_user, app.job_id, "read"):
            now_time = datetime.now(timezone.utc)
            expires = t.expires_at.replace(tzinfo=timezone.utc)
            is_overdue = now_time > expires
            stage = db.get(StageDefinition, t.stage_definition_id)
            candidate = db.get(Candidate, app.candidate_id)
            sla_alerts.append({
                "application_id": str(t.application_id),
                "candidate_name": candidate.full_name if candidate else "Candidate",
                "stage_name": stage.name if stage else "Unknown Stage",
                "entered_at": t.entered_at.isoformat(),
                "expires_at": t.expires_at.isoformat(),
                "status": "overdue" if is_overdue else "active",
                "priority_color": "#ef4444" if is_overdue else "#f59e0b"
            })

    # 2. Next candidate to review
    from models.enums import ApplicationStatus
    stmt = (
        select(Application)
        .options(selectinload(Application.candidate))
        .where(
            Application.company_id == current_user.company_id,
            Application.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.SCREENING])
        )
        .order_by(Application.match_score.desc().nullslast(), Application.created_at.asc())
    )
    apps = db.scalars(stmt).all()
    next_candidate = None
    for app in apps:
        if has_job_access(db, current_user, app.job_id, "read"):
            job = db.get(Job, app.job_id)
            next_candidate = {
                "application_id": str(app.id),
                "candidate_name": app.candidate.full_name,
                "job_title": job.title if job else "Unknown",
                "match_score": app.match_score,
                "stage": app.status.value
            }
            break

    # 3. Calendar agenda
    from models.interview import Interview
    stmt = (
        select(Interview)
        .where(
            Interview.company_id == current_user.company_id,
            Interview.interviewer_id == current_user.id,
            Interview.is_cancelled == False
        )
        .order_by(Interview.scheduled_at.asc())
    )
    interviews = db.scalars(stmt).all()
    agenda = []
    for iv in interviews:
        app = db.get(Application, iv.application_id)
        if app and has_job_access(db, current_user, app.job_id, "read"):
            candidate = db.get(Candidate, app.candidate_id)
            agenda.append({
                "interview_id": str(iv.id),
                "candidate_name": candidate.full_name if candidate else "Candidate",
                "title": iv.title,
                "scheduled_at": iv.scheduled_at.isoformat(),
                "duration_minutes": iv.duration_minutes
            })

    # 4. Recent notifications
    from models.ats_models import Notification
    stmt = (
        select(Notification)
        .where(
            Notification.company_id == current_user.company_id,
            Notification.user_id == current_user.id,
            Notification.status == "unread"
        )
        .order_by(Notification.created_at.desc())
        .limit(5)
    )
    notifs = db.scalars(stmt).all()
    recent_notifications = [{
        "id": str(n.id),
        "title": n.title,
        "message": n.message,
        "type": n.type,
        "created_at": n.created_at.isoformat()
    } for n in notifs]

    return {
        "sla_alerts": sla_alerts,
        "next_candidate": next_candidate,
        "calendar_agenda": agenda,
        "recent_notifications": recent_notifications
    }


@router.get("/summary")
@cached(namespace="dashboard_summary", ttl=120)
def get_dashboard_summary(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Returns an aggregated recruiter dashboard summary containing summary counts,
    pipeline stage distributions, overdue SLA candidates, calendar interviews,
    my assigned candidates, and jobs needing attention.
    """
    from datetime import datetime, timezone, timedelta
    from models.enums import ApplicationStatus
    from models.interview import Interview

    # 1. Pipeline: count candidates by current stage
    apps_stmt = select(Application).where(Application.company_id == current_user.company_id)
    all_apps = db.scalars(apps_stmt).all()

    visible_apps = [app for app in all_apps if has_job_access(db, current_user, app.job_id, "read")]

    pipeline_counts = {}
    for app in visible_apps:
        stage_id_str = str(app.current_stage_id) if app.current_stage_id else "unassigned"
        pipeline_counts[stage_id_str] = pipeline_counts.get(stage_id_str, 0) + 1

    # 2. Overdue candidates (SLA breaches)
    trackers = db.scalars(
        select(CandidateStageSLATracker)
        .join(Application, CandidateStageSLATracker.application_id == Application.id)
        .where(
            CandidateStageSLATracker.company_id == current_user.company_id,
            CandidateStageSLATracker.status.in_(["active", "breached"])
        )
    ).all()

    overdue = []
    now_time = datetime.now(timezone.utc)
    for t in trackers:
        app = db.get(Application, t.application_id)
        if app and has_job_access(db, current_user, app.job_id, "read"):
            expires = t.expires_at.replace(tzinfo=timezone.utc)
            is_overdue = now_time > expires
            if is_overdue:
                stage = db.get(StageDefinition, t.stage_definition_id)
                candidate = db.get(Candidate, app.candidate_id)
                overdue.append({
                    "application_id": str(t.application_id),
                    "candidate_name": candidate.full_name if candidate else "Candidate",
                    "stage_name": stage.name if stage else "Unknown Stage",
                    "entered_at": t.entered_at.isoformat(),
                    "expires_at": t.expires_at.isoformat()
                })

    # 3. Interviews
    int_stmt = (
        select(Interview)
        .where(
            Interview.company_id == current_user.company_id,
            Interview.interviewer_id == current_user.id,
            Interview.is_cancelled == False
        )
        .order_by(Interview.scheduled_at.asc())
    )
    scheduled_interviews = db.scalars(int_stmt).all()
    interviews_list = []
    for iv in scheduled_interviews:
        app = db.get(Application, iv.application_id)
        if app and has_job_access(db, current_user, app.job_id, "read"):
            candidate = db.get(Candidate, app.candidate_id)
            interviews_list.append({
                "interview_id": str(iv.id),
                "candidate_name": candidate.full_name if candidate else "Candidate",
                "title": iv.title,
                "scheduled_at": iv.scheduled_at.isoformat(),
                "duration_minutes": iv.duration_minutes
            })

    # 4. My candidates
    my_candidates = []
    for app in visible_apps:
        if app.owner_id == current_user.id:
            candidate = db.get(Candidate, app.candidate_id)
            job = db.get(Job, app.job_id)
            stage = db.get(StageDefinition, app.current_stage_id) if app.current_stage_id else None
            my_candidates.append({
                "application_id": str(app.id),
                "candidate_name": candidate.full_name if candidate else "Candidate",
                "job_title": job.title if job else "Unknown Job",
                "stage_name": stage.name if stage else app.status.value,
                "updated_at": app.updated_at.isoformat()
            })

    # 5. Summary counts
    total_candidates = len(set(app.candidate_id for app in visible_apps))
    active_statuses = {ApplicationStatus.SUBMITTED, ApplicationStatus.SCREENING, ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER}
    active_apps = [a for a in visible_apps if a.status in active_statuses]
    summary = {
        "total_applications": len(visible_apps),
        "active_applications": len(active_apps),
        "total_candidates": total_candidates,
        "overdue_count": len(overdue),
        "my_candidates_count": len(my_candidates),
    }

    # 6. Jobs needing attention
    job_stats = {}
    for app in visible_apps:
        if app.status in {ApplicationStatus.SUBMITTED, ApplicationStatus.SCREENING}:
            job_stats[app.job_id] = job_stats.get(app.job_id, 0) + 1
    
    sorted_job_ids = sorted(job_stats.keys(), key=lambda j: job_stats[j], reverse=True)
    jobs_needing_attention = []
    for j_id in sorted_job_ids[:5]:
        job = db.get(Job, j_id)
        if job:
            jobs_needing_attention.append({
                "job_id": str(job.id),
                "job_title": job.title,
                "department": job.department,
                "unreviewed_count": job_stats[j_id]
            })

    return {
        "summary": summary,
        "pipeline": pipeline_counts,
        "overdue": overdue,
        "interviews": interviews_list,
        "my_candidates": my_candidates,
        "jobs_needing_attention": jobs_needing_attention
    }
