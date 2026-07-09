from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import Application, Offer, CandidateTask, CandidateDocument, Notification, Interview, Candidate
from datetime import datetime, timezone

router = APIRouter(prefix="/candidate/dashboard", tags=["candidate-dashboard"])

@router.get("")
def get_dashboard(
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # 1. Fetch applications
    apps = []
    if candidate_ids:
        apps = db.scalars(
            select(Application).where(Application.candidate_id.in_(candidate_ids))
        ).all()

    # 2. Fetch offers
    app_ids = [app.id for app in apps]
    offers = []
    if app_ids:
        offers = db.scalars(
            select(Offer).where(Offer.application_id.in_(app_ids))
        ).all()

    # 3. Fetch onboarding tasks
    tasks = db.scalars(
        select(CandidateTask).where(CandidateTask.candidate_id == current_candidate.id)
    ).all()

    # 4. Fetch upcoming interviews
    interviews = []
    if app_ids:
        interviews = db.scalars(
            select(Interview)
            .where(Interview.application_id.in_(app_ids))
            .where(Interview.scheduled_at > datetime.now(timezone.utc))
            .where(Interview.is_cancelled == False)
        ).all()

    # 5. Fetch pending documents
    pending_docs_count = 0
    if app_ids:
        pending_docs_count = db.scalar(
            select(func.count(CandidateDocument.id))
            .where(CandidateDocument.application_id.in_(app_ids))
            .where(CandidateDocument.status == "pending")
        ) or 0

    # 6. Compute workspace state (Derived, never persisted)
    # States: Completed, Onboarding, Offer Accepted, Offer Declined, Offer Pending, Interviewing, Application Submitted
    computed_state = "Application Submitted"

    has_completed_app = any(app.status == "hired" for app in apps)
    has_onboarding_task = any(task.status in ["pending", "needs_review", "rejected"] for task in tasks) or any(app.status == "onboarding" for app in apps)
    has_accepted_offer = any(offer.status == "accepted" for offer in offers)
    has_declined_offer = any(offer.status == "declined" for offer in offers)
    has_pending_offer = any(offer.status == "sent" for offer in offers)
    has_upcoming_interview = len(interviews) > 0
    has_active_apps = len(apps) > 0

    if has_completed_app:
        computed_state = "Completed"
    elif has_onboarding_task:
        computed_state = "Onboarding"
    elif has_accepted_offer:
        computed_state = "Offer Accepted"
    elif has_declined_offer:
        computed_state = "Offer Declined"
    elif has_pending_offer:
        computed_state = "Offer Pending"
    elif has_upcoming_interview:
        computed_state = "Interviewing"
    elif has_active_apps:
        computed_state = "Application Submitted"

    # 7. Fetch Notifications & Unread Counts
    db_notifications = db.scalars(
        select(Notification)
        .where(Notification.user_id == current_candidate.id)
        .order_by(Notification.created_at.desc())
    ).all()

    unread_count = sum(1 for n in db_notifications if n.status == "unread")
    
    # Notification grouping summary logic
    # e.g. "3 interview reminders", "2 messages"
    type_counts = {}
    for n in db_notifications:
        if n.status == "unread":
            type_counts[n.type] = type_counts.get(n.type, 0) + 1

    grouped_summaries = []
    for n_type, count in type_counts.items():
        if n_type == "interview":
            label = f"{count} interview reminder{'s' if count > 1 else ''}"
        elif n_type == "message":
            label = f"{count} new message{'s' if count > 1 else ''}"
        elif n_type == "offer":
            label = f"{count} offer update{'s' if count > 1 else ''}"
        elif n_type == "document":
            label = f"{count} document request{'s' if count > 1 else ''}"
        elif n_type == "tasks":
            label = f"{count} pending task{'s' if count > 1 else ''}"
        else:
            label = f"{count} {n_type} update{'s' if count > 1 else ''}"
        grouped_summaries.append(label)

    notifications_list = [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in db_notifications
    ]

    return {
        "computed_state": computed_state,
        "metrics": {
            "applications_count": len(apps),
            "upcoming_interviews_count": len(interviews),
            "pending_tasks_count": len([t for t in tasks if t.status != "completed"]),
            "pending_documents_count": pending_docs_count,
        },
        "notifications": notifications_list,
        "unread_count": unread_count,
        "grouped_summary": grouped_summaries,
        "grouped_notifications": grouped_summaries,
        "recent_notifications": notifications_list[:10]  # Show recent 10 notifications
    }
