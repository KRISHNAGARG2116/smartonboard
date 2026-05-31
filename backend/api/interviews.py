import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import RequireRecruiter, TenantDb
from models import Application, Interview, Scorecard, User, Job
from models.enums import ApplicationStatus
from celery_worker import (
    track_stage_transition_async,
    track_recruiter_productivity_async,
)
from schemas.interview import (
    InterviewCreateRequest,
    InterviewResponse,
    InterviewUpdateRequest,
    InterviewNotificationDraftResponse,
)
from schemas.scorecard import ScorecardSubmitRequest, ScorecardResponse
from core.audit import log_audit_event

router = APIRouter(prefix="/applications/{application_id}/interviews", tags=["interviews"])


def _get_application(application_id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter) -> Application:
    app_record = db.scalar(
        select(Application)
        .options(
            selectinload(Application.candidate),
            selectinload(Application.job)
        )
        .where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app_record


def _generate_notification_draft(
    application: Application,
    interview_id: uuid.UUID,
    body: InterviewCreateRequest,
    interviewer: User,
) -> InterviewNotificationDraftResponse:
    candidate_name = application.candidate.full_name if application.candidate else "Candidate"
    job_title = application.job.title if application.job else "Job Role"
    scheduled_time = body.scheduled_at.isoformat()
    interview_stage = body.stage
    scorecard_link = f"/api/v1/applications/{application.id}/interviews/{interview_id}/scorecard"

    draft_subject = f"Interview Scheduled: {candidate_name} - {body.title}"
    draft_body = (
        f"Hello {interviewer.full_name},\n\n"
        f"You have been assigned to conduct the '{body.title}' ({interview_stage} stage) interview for candidate {candidate_name} "
        f"applying for the position of '{job_title}'.\n\n"
        f"Scheduled Time: {scheduled_time}\n"
        f"Duration: {body.duration_minutes} minutes\n"
        f"Video Conference Link: {body.video_link or 'N/A'}\n\n"
        f"Please conduct the evaluation and submit your scorecard using the link below:\n"
        f"Scorecard URL: {scorecard_link}\n\n"
        f"Best regards,\n"
        f"SmartOnboard Recruitment Team"
    )

    return InterviewNotificationDraftResponse(
        recipient_email=interviewer.email,
        recipient_name=interviewer.full_name,
        subject=draft_subject,
        body=draft_body,
        draft_payload={
            "candidate_name": candidate_name,
            "job_title": job_title,
            "scheduled_time": scheduled_time,
            "interview_stage": interview_stage,
            "scorecard_link": scorecard_link,
            "video_link": body.video_link,
            "duration_minutes": body.duration_minutes
        }
    )


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def schedule_interview(
    application_id: uuid.UUID,
    body: InterviewCreateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    # Verify interviewer exists and belongs to the same company
    interviewer = db.scalar(
        select(User).where(
            User.id == body.interviewer_id,
            User.company_id == current_user.company_id
        )
    )
    if not interviewer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interviewer user not found in this company"
        )

    # 1. Schedule Interview Record
    interview = Interview(
        company_id=current_user.company_id,
        application_id=application_id,
        interviewer_id=body.interviewer_id,
        title=body.title,
        stage=body.stage,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
        video_link=body.video_link
    )
    db.add(interview)

    # 2. Check and execute automatic stage transition: SCREENING -> INTERVIEW
    previous_status = app_record.status.value
    new_status = previous_status
    status_changed = False

    if app_record.status == ApplicationStatus.SCREENING:
        app_record.status = ApplicationStatus.INTERVIEW
        new_status = ApplicationStatus.INTERVIEW.value
        status_changed = True

    db.commit()
    db.refresh(interview)
    if status_changed:
        db.refresh(app_record)

    # Dispatch background tracking tasks
    track_recruiter_productivity_async.delay(
        str(current_user.company_id),
        str(current_user.id),
        "interview"
    )
    if status_changed:
        track_stage_transition_async.delay(
            str(current_user.company_id),
            str(application_id),
            previous_status,
            new_status,
            str(current_user.id)
        )

    # 3. Log Audit Events
    # Event 1: interview.scheduled
    log_audit_event(
        db=db,
        action="interview.scheduled",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="interviews",
        resource_id=str(interview.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "interview_id": str(interview.id),
            "actor_id": str(current_user.id),
            "previous_status": previous_status,
            "new_status": new_status
        }
    )

    # Event 2: application.status_changed (if automatic transition occurred)
    if status_changed:
        log_audit_event(
            db=db,
            action="application.status_changed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="applications",
            resource_id=str(application_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "application_id": str(application_id),
                "candidate_id": str(app_record.candidate_id),
                "actor_id": str(current_user.id),
                "previous_status": previous_status,
                "new_status": new_status,
                "trigger_event": "interview.scheduled"
            }
        )

    # 4. Generate notification draft
    draft = _generate_notification_draft(app_record, interview.id, body, interviewer)

    # Map the response properties safely
    resp = InterviewResponse.model_validate(interview)
    resp.notification_draft = draft
    return resp


@router.get("", response_model=List[InterviewResponse])
def list_interviews(
    application_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    # Verify application exists
    _get_application(application_id, db, current_user)

    stmt = select(Interview).where(
        Interview.application_id == application_id,
        Interview.company_id == current_user.company_id
    ).order_by(Interview.scheduled_at.asc())

    return list(db.scalars(stmt).all())


@router.patch("/{interview_id}", response_model=InterviewResponse)
def update_interview(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    body: InterviewUpdateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    interview = db.scalar(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.application_id == application_id,
            Interview.company_id == current_user.company_id
        )
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    is_cancelled_transition = False
    if body.is_cancelled is not None and body.is_cancelled != interview.is_cancelled:
        if body.is_cancelled is True:
            is_cancelled_transition = True
        interview.is_cancelled = body.is_cancelled

    if body.interviewer_id is not None:
        interviewer = db.scalar(
            select(User).where(
                User.id == body.interviewer_id,
                User.company_id == current_user.company_id
            )
        )
        if not interviewer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interviewer user not found in this company"
            )
        interview.interviewer_id = body.interviewer_id

    if body.title is not None:
        interview.title = body.title
    if body.stage is not None:
        interview.stage = body.stage
    if body.scheduled_at is not None:
        interview.scheduled_at = body.scheduled_at
    if body.duration_minutes is not None:
        interview.duration_minutes = body.duration_minutes
    if body.video_link is not None:
        interview.video_link = body.video_link

    db.commit()
    db.refresh(interview)

    # Log audit event
    action = "interview.cancelled" if is_cancelled_transition else "interview.updated"
    log_audit_event(
        db=db,
        action=action,
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="interviews",
        resource_id=str(interview.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "interview_id": str(interview.id),
            "actor_id": str(current_user.id),
            "previous_status": app_record.status.value,
            "new_status": app_record.status.value
        }
    )

    return interview


@router.post("/{interview_id}/scorecard", response_model=ScorecardResponse, status_code=status.HTTP_201_CREATED)
def submit_scorecard(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    body: ScorecardSubmitRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    interview = db.scalar(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.application_id == application_id,
            Interview.company_id == current_user.company_id
        )
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Verify if scorecard already exists
    existing = db.scalar(select(Scorecard).where(Scorecard.interview_id == interview_id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scorecard already submitted for this interview"
        )

    # 1. Fetch Job criteria template rules from Job.settings
    job = db.scalar(select(Job).where(Job.id == app_record.job_id))
    configured_criteria = None
    if job and job.settings:
        configured_criteria = job.settings.get("scorecard_criteria")

    # Fallback default if not explicitly configured in Job.settings
    if not configured_criteria:
        configured_criteria = ["coding", "system_design", "communication"]

    # 2. Enforce Structured Hiring consistency: Submitted keys must match configured template criteria
    submitted_keys = set(body.criteria_scores.keys())
    template_keys = set(configured_criteria)
    
    if submitted_keys != template_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scorecard criteria mismatch. Expected exactly: {configured_criteria}. Got: {list(body.criteria_scores.keys())}"
        )

    # 3. Create & Submit Scorecard (we record both scorecard.created and scorecard.submitted events to be fully compliant)
    scorecard = Scorecard(
        company_id=current_user.company_id,
        application_id=application_id,
        interview_id=interview_id,
        grader_id=current_user.id,
        criteria_scores=body.criteria_scores,
        overall_recommendation=body.overall_recommendation,
        notes=body.notes,
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(scorecard)
    db.commit()
    db.refresh(scorecard)

    # 4. Log scorecard.created
    log_audit_event(
        db=db,
        action="scorecard.created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="scorecards",
        resource_id=str(scorecard.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "interview_id": str(interview_id),
            "actor_id": str(current_user.id),
            "scorecard_id": str(scorecard.id),
            "previous_status": app_record.status.value,
            "new_status": app_record.status.value
        }
    )

    # 5. Log scorecard.submitted
    log_audit_event(
        db=db,
        action="scorecard.submitted",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="scorecards",
        resource_id=str(scorecard.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "interview_id": str(interview_id),
            "actor_id": str(current_user.id),
            "scorecard_id": str(scorecard.id),
            "previous_status": app_record.status.value,
            "new_status": app_record.status.value,
            "overall_recommendation": body.overall_recommendation
        }
    )

    return scorecard


@router.get("/{interview_id}/scorecard", response_model=ScorecardResponse)
def get_scorecard(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    _get_application(application_id, db, current_user)

    # Verify interview exists
    interview = db.scalar(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.application_id == application_id,
            Interview.company_id == current_user.company_id
        )
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    scorecard = db.scalar(
        select(Scorecard).where(
            Scorecard.interview_id == interview_id,
            Scorecard.company_id == current_user.company_id
        )
    )
    if not scorecard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")
        
    return scorecard
