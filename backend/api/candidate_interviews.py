from typing import Annotated
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.deps import CurrentCandidate, get_db, VerifiedCandidate
from db.session import tenant_context
from models import Interview, InterviewSlot, User, CalendarCredentials, Application, Candidate
from core.vault import SecretVaultService
from core.calendar_provider import GoogleCalendarProvider, MicrosoftGraphProvider
from core.audit import log_audit_event
from tasks.calendar_sync import acquire_sync_lock, release_sync_lock

router = APIRouter(prefix="/candidate", tags=["Candidate Interviews"])


class RescheduleRequest(BaseModel):
    new_start_time: datetime


def get_provider_instance(provider_name: str):
    if provider_name.lower() == "google":
        return GoogleCalendarProvider()
    elif provider_name.lower() in ("outlook", "microsoft"):
        return MicrosoftGraphProvider()
    else:
        raise ValueError(f"Unsupported calendar provider: {provider_name}")


@router.get("/interviews")
def get_candidate_interviews(
    current_candidate: CurrentCandidate,
    db: Annotated[Session, Depends(get_db)]
):
    """Retrieve all scheduled interviews and confirmed booking slots for the candidate.
    
    Excludes sensitive raw booking tokens.
    """
    with tenant_context(auth_mode="true"):
        # Query candidates by email
        candidates = db.scalars(
            select(Candidate).where(Candidate.email == current_candidate.email.lower())
        ).all()
        candidate_ids = [c.id for c in candidates]
        
        if not candidate_ids:
            return []
            
        # Fetch applications
        apps = db.scalars(
            select(Application).where(Application.candidate_id.in_(candidate_ids))
        ).all()
        app_ids = [a.id for a in apps]
        
        if not app_ids:
            return []
            
        # Query all interviews matching these applications
        stmt = (
            select(Interview)
            .options(
                selectinload(Interview.application).selectinload(Application.job),
                selectinload(Interview.application).selectinload(Application.company),
                selectinload(Interview.interviewer)
            )
            .where(Interview.application_id.in_(app_ids))
            .order_by(Interview.scheduled_at.desc())
        )
        interviews = db.scalars(stmt).all()
        
        results = []
        for iv in interviews:
            # Query confirmed slots for this interview
            slot = db.scalar(
                select(InterviewSlot)
                .where(
                    InterviewSlot.interview_id == iv.id,
                    InterviewSlot.status == "confirmed"
                )
            )
            
            results.append({
                "id": str(iv.id),
                "title": iv.title,
                "stage": iv.stage,
                "scheduled_at": iv.scheduled_at.isoformat(),
                "duration_minutes": iv.duration_minutes,
                "video_link": iv.video_link,
                "is_cancelled": iv.is_cancelled,
                "company_name": iv.application.company.name if iv.application.company else "Unknown Company",
                "job_title": iv.application.job.title if iv.application.job else "Unknown Position",
                "interviewer_name": iv.interviewer.full_name if iv.interviewer else "Interviewer",
                "slot": {
                    "id": str(slot.id),
                    "start_time": slot.start_time.isoformat(),
                    "end_time": slot.end_time.isoformat(),
                    "status": slot.status
                } if slot else None
            })
            
        return results


@router.post("/bookings/{slot_id}/cancel")
def cancel_candidate_booking(
    slot_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_candidate: CurrentCandidate
):
    """Authenticate and cancel a candidate slot booking using active credentials."""
    with tenant_context(auth_mode="true"):
        slot = db.scalar(
            select(InterviewSlot)
            .options(selectinload(InterviewSlot.interview).selectinload(Interview.application).selectinload(Application.candidate))
            .where(InterviewSlot.id == slot_id)
        )
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking slot not found"
        )
        
    # Verify ownership
    app = slot.interview.application
    if not app.candidate or app.candidate.email != current_candidate.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel this booking"
        )
        
    with tenant_context(tenant_id=str(slot.company_id)):
        slot.status = "cancelled"
        db.add(slot)
        db.commit()
        
        # External cancel invite if provider is connected
        interview = db.scalar(select(Interview).where(Interview.id == slot.interview_id))
        interviewer = db.scalar(select(User).where(User.id == interview.interviewer_id))
        cred = db.scalar(
            select(CalendarCredentials).where(
                CalendarCredentials.user_id == interviewer.id,
                CalendarCredentials.company_id == slot.company_id
            )
        )
        if cred and cred.status == "active" and slot.external_event_id:
            provider = get_provider_instance(cred.provider)
            vault = SecretVaultService()
            try:
                decrypted_access = vault.decrypt_secret(cred.encrypted_access_token)
                provider.cancel_event(
                    email=cred.account_email,
                    access_token=decrypted_access,
                    external_event_id=slot.external_event_id
                )
            except Exception:
                pass
                
        # Log audit event
        log_audit_event(
            db=db,
            action="schedule.slot_cancelled",
            actor_type="CANDIDATE",
            actor_id=current_candidate.id,
            company_id=slot.company_id,
            resource_type="interviews",
            resource_id=str(slot.interview_id),
            metadata={
                "interview_id": str(slot.interview_id),
                "slot_id": str(slot.id),
                "reason": "Cancelled via Candidate Portal"
            }
        )
        
    return {"status": "cancelled", "message": "Interview successfully cancelled."}


@router.post("/bookings/{slot_id}/reschedule")
def reschedule_candidate_booking(
    slot_id: uuid.UUID,
    body: RescheduleRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_candidate: VerifiedCandidate
):
    """Authenticate and reschedule an active booking to a new time block."""
    with tenant_context(auth_mode="true"):
        slot = db.scalar(
            select(InterviewSlot)
            .options(selectinload(InterviewSlot.interview).selectinload(Interview.application).selectinload(Application.candidate))
            .where(InterviewSlot.id == slot_id)
        )
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking slot not found"
        )
        
    # Verify ownership
    app = slot.interview.application
    if not app.candidate or app.candidate.email != current_candidate.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to reschedule this booking"
        )
        
    with tenant_context(tenant_id=str(slot.company_id)):
        interview = db.scalar(select(Interview).where(Interview.id == slot.interview_id))
        duration = timedelta(minutes=interview.duration_minutes)
        new_start = body.new_start_time
        new_end = new_start + duration
        
        # Concurrency lock
        if not acquire_sync_lock(f"book:{interview.id}"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent booking active. Please retry slot selection."
            )
            
        try:
            # Check overlap in DB
            existing_overlap = db.scalar(
                select(InterviewSlot).where(
                    InterviewSlot.interview_id == interview.id,
                    InterviewSlot.status == "confirmed",
                    InterviewSlot.id != slot.id,  # ignore self
                    InterviewSlot.start_time < new_end,
                    InterviewSlot.end_time > new_start
                )
            )
            if existing_overlap:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This slot time block has already been reserved"
                )
                
            old_start = slot.start_time
            interviewer = db.scalar(select(User).where(User.id == interview.interviewer_id))
            cred = db.scalar(
                select(CalendarCredentials).where(
                    CalendarCredentials.user_id == interviewer.id,
                    CalendarCredentials.company_id == slot.company_id
                )
            )
            
            # Cancel old calendar invite
            if cred and cred.status == "active" and slot.external_event_id:
                provider = get_provider_instance(cred.provider)
                vault = SecretVaultService()
                try:
                    decrypted_access = vault.decrypt_secret(cred.encrypted_access_token)
                    provider.cancel_event(
                        email=cred.account_email,
                        access_token=decrypted_access,
                        external_event_id=slot.external_event_id
                    )
                except Exception:
                    pass
                    
            # Update slot details
            slot.start_time = new_start
            slot.end_time = new_end
            slot.external_event_id = None
            db.add(slot)
            
            try:
                db.commit()
                db.refresh(slot)
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Overlapping reschedule slot reservation rejected by exclusion checks."
                ) from e
                
            # Create new calendar invite
            if cred and cred.status == "active":
                provider = get_provider_instance(cred.provider)
                vault = SecretVaultService()
                try:
                    decrypted_access = vault.decrypt_secret(cred.encrypted_access_token)
                    ext_id = provider.book_event(
                        email=cred.account_email,
                        access_token=decrypted_access,
                        start=new_start,
                        end=new_end,
                        subject=f"SmartOnboard Rescheduled Interview: {interviewer.full_name}",
                        description=""
                    )
                    slot.external_event_id = ext_id
                    db.add(slot)
                    db.commit()
                except Exception:
                    pass
                    
            # Log audit event
            log_audit_event(
                db=db,
                action="schedule.rescheduled",
                actor_type="CANDIDATE",
                actor_id=current_candidate.id,
                company_id=slot.company_id,
                resource_type="interviews",
                resource_id=str(slot.interview_id),
                metadata={
                    "interview_id": str(slot.interview_id),
                    "slot_id": str(slot.id),
                    "old_start_time": old_start.isoformat(),
                    "new_start_time": new_start.isoformat()
                }
            )
            
        finally:
            release_sync_lock(f"book:{interview.id}")
            
    return {
        "status": "confirmed",
        "slot_id": str(slot.id),
        "start_time": slot.start_time,
        "end_time": slot.end_time
    }
