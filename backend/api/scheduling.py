import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.deps import get_tenant_db, get_current_user
from models import User, Company, CalendarCredentials, OAuthState, SchedulingLink, InterviewSlot, Interview
from models.enums import UserRole
from core.vault import SecretVaultService
from core.calendar_provider import GoogleCalendarProvider, MicrosoftGraphProvider
from core.audit import log_audit_event
from db.session import tenant_context
from tasks.calendar_sync import acquire_sync_lock, release_sync_lock

router = APIRouter(prefix="/schedule", tags=["schedule"])


class CreateLinkRequest(BaseModel):
    interview_id: str
    expires_in_days: int = 3
    one_time_use: bool = True


class CreateLinkResponse(BaseModel):
    link_id: str
    raw_token: str
    expires_at: datetime
    booking_url: str


class BookRequest(BaseModel):
    start_time: datetime
    candidate_notes: str | None = None


class BookResponse(BaseModel):
    status: str
    slot_id: str
    start_time: datetime
    end_time: datetime
    booking_token: str


class CancelRequest(BaseModel):
    reason: str | None = None


class RescheduleRequest(BaseModel):
    new_start_time: datetime


def get_provider_instance(provider_name: str):
    if provider_name.lower() == "google":
        return GoogleCalendarProvider()
    elif provider_name.lower() in ("outlook", "microsoft"):
        return MicrosoftGraphProvider()
    else:
        raise ValueError(f"Unsupported calendar provider: {provider_name}")


@router.post("/links", response_model=CreateLinkResponse, status_code=status.HTTP_201_CREATED)
def create_scheduling_link(
    request: Request,
    body: CreateLinkRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_tenant_db)
):
    # Verify the interview exists and belongs to the company
    interview = db.scalar(
        select(Interview).where(
            Interview.id == body.interview_id,
            Interview.company_id == current_user.company_id
        )
    )
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    # Generate a cryptographically secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    # Save SchedulingLink inside RLS tenant context
    link = SchedulingLink(
        company_id=current_user.company_id,
        interview_id=interview.id,
        token_hash=token_hash,
        expires_at=expires_at,
        one_time_use=body.one_time_use
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    # Log schedule.link_created audit event
    log_audit_event(
        db=db,
        action="schedule.link_created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "interview_id": str(interview.id),
            "expires_at": expires_at.isoformat(),
            "one_time_use": body.one_time_use
        }
    )

    booking_url = f"https://smartonboard.com/schedule/{raw_token}"
    return CreateLinkResponse(
        link_id=str(link.id),
        raw_token=raw_token,
        expires_at=expires_at,
        booking_url=booking_url
    )


@router.get("/{raw_token}/availability")
def get_slots_availability(
    raw_token: str,
    request: Request,
    db: Session = Depends(get_tenant_db)
):
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Public endpoint operates under dynamic tenant context from the pre-hashed lookup
    # Run under RLS bypass to locate the target SchedulingLink company boundary safely
    with tenant_context(auth_mode="true"):
        link = db.scalar(select(SchedulingLink).where(SchedulingLink.token_hash == token_hash))
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduling link not found"
        )

    # Run in tenant context matching company ID of the link
    with tenant_context(tenant_id=str(link.company_id)):
        # 1. Enforce link expiry and one-time use validations
        if link.expires_at < datetime.now(timezone.utc):
            log_audit_event(
                db=db,
                action="schedule.link_expired",
                actor_type="UNAUTHENTICATED",
                company_id=link.company_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"interview_id": str(link.interview_id), "cause": "TTL Exceeded"}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This scheduling link has expired"
            )

        if link.one_time_use and link.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This scheduling link has already been consumed"
            )

        # 2. Fetch target interview and interviewer details
        interview = db.scalar(select(Interview).where(Interview.id == link.interview_id))
        interviewer = db.scalar(select(User).where(User.id == interview.interviewer_id))
        
        # 3. Retrieve calendar credentials for interviewer
        cred = db.scalar(
            select(CalendarCredentials).where(
                CalendarCredentials.user_id == interviewer.id,
                CalendarCredentials.company_id == link.company_id
            )
        )

        if not cred or cred.status != "active":
            # If no active connected calendar, fallback to empty availability grid
            return {
                "interview_id": str(interview.id),
                "interviewer_name": interviewer.full_name,
                "duration_minutes": interview.duration_minutes,
                "available_slots": []
            }

        # 4. Resolve free/busy calendars dynamically
        provider = get_provider_instance(cred.provider)
        vault = SecretVaultService()
        try:
            decrypted_access = vault.decrypt_secret(cred.encrypted_access_token)
            
            # Request busy times from provider for next 7 days
            start_window = datetime.now(timezone.utc)
            end_window = start_window + timedelta(days=7)
            busy_ranges = provider.fetch_busy_slots(
                email=cred.account_email,
                access_token=decrypted_access,
                start=start_window,
                end=end_window
            )
        except Exception:
            busy_ranges = []

        # 5. Define Grid working hours (e.g. 9:00 to 17:00 local, simulated for UTC 9:00 to 17:00)
        duration = timedelta(minutes=interview.duration_minutes)
        available_slots = []
        
        # Scan 7 days slot matrix
        for day in range(1, 4):
            day_start = (datetime.now(timezone.utc) + timedelta(days=day)).replace(hour=9, minute=0, second=0, microsecond=0)
            day_end = day_start.replace(hour=17, minute=0)
            
            cursor = day_start
            while cursor + duration <= day_end:
                slot_start = cursor
                slot_end = cursor + duration
                
                # Check overlapping with busy ranges
                overlap = False
                for busy_start, busy_end in busy_ranges:
                    # ensure busy datetimes are timezone aware
                    if busy_start.tzinfo is None:
                        busy_start = busy_start.replace(tzinfo=timezone.utc)
                    if busy_end.tzinfo is None:
                        busy_end = busy_end.replace(tzinfo=timezone.utc)
                        
                    if not (slot_end <= busy_start or slot_start >= busy_end):
                        overlap = True
                        break
                
                # Check overlapping with database confirmed slots for this interview
                if not overlap:
                    confirmed_overlap = db.scalar(
                        select(InterviewSlot).where(
                            InterviewSlot.interview_id == interview.id,
                            InterviewSlot.status == "confirmed",
                            InterviewSlot.start_time < slot_end,
                            InterviewSlot.end_time > slot_start
                        )
                    )
                    if confirmed_overlap:
                        overlap = True

                if not overlap:
                    available_slots.append({
                        "start_time": slot_start.isoformat(),
                        "end_time": slot_end.isoformat()
                    })
                
                cursor += duration

        return {
            "interview_id": str(interview.id),
            "interviewer_name": interviewer.full_name,
            "duration_minutes": interview.duration_minutes,
            "available_slots": available_slots
        }


@router.post("/{raw_token}/book", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def book_schedule_slot(
    raw_token: str,
    request: Request,
    body: BookRequest,
    db: Session = Depends(get_tenant_db)
):
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # RLS bypass to locate link company boundary
    with tenant_context(auth_mode="true"):
        link = db.scalar(select(SchedulingLink).where(SchedulingLink.token_hash == token_hash))
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduling link not found"
        )

    # Execute inside company tenant boundaries
    with tenant_context(tenant_id=str(link.company_id)):
        # 1. Enforce Link validations
        if link.expires_at < datetime.now(timezone.utc):
            log_audit_event(
                db=db,
                action="schedule.link_expired",
                actor_type="UNAUTHENTICATED",
                company_id=link.company_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"interview_id": str(link.interview_id), "cause": "TTL Exceeded"}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Scheduling link has expired"
            )

        if link.one_time_use and link.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Scheduling link has already been consumed"
            )

        interview = db.scalar(select(Interview).where(Interview.id == link.interview_id))
        duration = timedelta(minutes=interview.duration_minutes)
        start_time = body.start_time
        end_time = start_time + duration

        # 2. Acquire Redis Distributed Concurrency Lock
        if not acquire_sync_lock(f"book:{interview.id}"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent booking active. Please retry slot selection."
            )

        try:
            # 3. Check for overlapping confirmed slots in DB first
            # The exclude_overlapping_confirmed_bookings constraint also checks this at database-level
            existing_overlap = db.scalar(
                select(InterviewSlot).where(
                    InterviewSlot.interview_id == interview.id,
                    InterviewSlot.status == "confirmed",
                    InterviewSlot.start_time < end_time,
                    InterviewSlot.end_time > start_time
                )
            )
            if existing_overlap:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This slot time block has already been reserved"
                )

            # 4. Generate candidate booking ownership tokens
            booking_token = secrets.token_urlsafe(32)
            booking_token_hash = hashlib.sha256(booking_token.encode("utf-8")).hexdigest()

            # 5. Write confirmed slot
            slot = InterviewSlot(
                company_id=link.company_id,
                interview_id=interview.id,
                start_time=start_time,
                end_time=end_time,
                status="confirmed",
                booking_token_hash=booking_token_hash
            )
            db.add(slot)

            # Consume Link
            link.used_at = datetime.now(timezone.utc)
            db.add(link)
            
            # Commit atomically - trigger btree_gist EXCLUDE overlap constraints check
            try:
                db.commit()
                db.refresh(slot)
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Overlapping slot reservation rejected by exclusion safety checks."
                ) from e

            # 6. Dispatch External Calendar Invite invite if provider connected
            interviewer = db.scalar(select(User).where(User.id == interview.interviewer_id))
            cred = db.scalar(
                select(CalendarCredentials).where(
                    CalendarCredentials.user_id == interviewer.id,
                    CalendarCredentials.company_id == link.company_id
                )
            )
            if cred and cred.status == "active":
                provider = get_provider_instance(cred.provider)
                vault = SecretVaultService()
                try:
                    decrypted_access = vault.decrypt_secret(cred.encrypted_access_token)
                    ext_id = provider.book_event(
                        email=cred.account_email,
                        access_token=decrypted_access,
                        start=start_time,
                        end=end_time,
                        subject=f"SmartOnboard Interview: {interviewer.full_name}",
                        description=body.candidate_notes or ""
                    )
                    slot.external_event_id = ext_id
                    db.add(slot)
                    db.commit()

                    # Emit billing event
                    from core.workflow_engine import emit_billing_event
                    emit_billing_event(db, link.company_id, "calendar.booking.created", str(slot.id))


                    log_audit_event(
                        db=db,
                        action="schedule.calendar_event_created",
                        actor_type="SYSTEM",
                        company_id=link.company_id,
                        metadata={"provider": cred.provider, "external_event_id": ext_id}
                    )
                except Exception as cal_err:
                    log_audit_event(
                        db=db,
                        action="schedule.calendar_event_failed",
                        actor_type="SYSTEM",
                        company_id=link.company_id,
                        metadata={"provider": cred.provider, "error": str(cal_err)}
                    )

            # Log schedule.slot_booked audit event
            log_audit_event(
                db=db,
                action="schedule.slot_booked",
                actor_type="UNAUTHENTICATED",
                company_id=link.company_id,
                metadata={
                    "interview_id": str(interview.id),
                    "slot_id": str(slot.id),
                    "start_time": start_time.isoformat()
                }
            )

            # Emit simulated reminder_sent
            log_audit_event(
                db=db,
                action="schedule.reminder_sent",
                actor_type="SYSTEM",
                company_id=link.company_id,
                metadata={"interview_id": str(interview.id), "delivery_channel": "email"}
            )
            db.commit()

            return BookResponse(
                status="confirmed",
                slot_id=str(slot.id),
                start_time=start_time,
                end_time=end_time,
                booking_token=booking_token
            )

        finally:
            # Release distributed lock
            release_sync_lock(f"book:{interview.id}")


@router.post("/bookings/{slot_id}/cancel")
def cancel_schedule_booking(
    slot_id: str,
    request: Request,
    body: CancelRequest,
    x_booking_token: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_tenant_db)
):
    if not x_booking_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ownership booking token"
        )

    # RLS bypass to locate slot company boundary
    with tenant_context(auth_mode="true"):
        slot = db.scalar(select(InterviewSlot).where(InterviewSlot.id == slot_id))
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking slot not found"
        )

    # Verify ownership token
    booking_token_hash = hashlib.sha256(x_booking_token.encode("utf-8")).hexdigest()
    if slot.booking_token_hash != booking_token_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid booking ownership token validation failed"
        )

    with tenant_context(tenant_id=str(slot.company_id)):
        slot.status = "cancelled"
        db.add(slot)
        db.commit()

        # External Cancel Calendar Invite if connected
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

        # Log schedule.slot_cancelled audit event
        log_audit_event(
            db=db,
            action="schedule.slot_cancelled",
            actor_type="UNAUTHENTICATED",
            company_id=slot.company_id,
            metadata={
                "interview_id": str(slot.interview_id),
                "slot_id": str(slot.id),
                "reason": body.reason or "Cancelled by candidate"
            }
        )
        db.commit()

    return {"status": "cancelled", "message": "Interview successfully cancelled."}


@router.post("/bookings/{slot_id}/reschedule")
def reschedule_schedule_booking(
    slot_id: str,
    request: Request,
    body: RescheduleRequest,
    x_booking_token: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_tenant_db)
):
    if not x_booking_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ownership booking token"
        )

    # RLS bypass to locate slot company boundary
    with tenant_context(auth_mode="true"):
        slot = db.scalar(select(InterviewSlot).where(InterviewSlot.id == slot_id))
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking slot not found"
        )

    # Verify ownership token
    booking_token_hash = hashlib.sha256(x_booking_token.encode("utf-8")).hexdigest()
    if slot.booking_token_hash != booking_token_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid booking ownership token validation failed"
        )

    with tenant_context(tenant_id=str(slot.company_id)):
        interview = db.scalar(select(Interview).where(Interview.id == slot.interview_id))
        duration = timedelta(minutes=interview.duration_minutes)
        new_start = body.new_start_time
        new_end = new_start + duration

        # Concurrency Lock
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
                    InterviewSlot.id != slot.id, # ignore self
                    InterviewSlot.start_time < new_end,
                    InterviewSlot.end_time > new_start
                )
            )
            if existing_overlap:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This slot time block has already been reserved"
                )

            # Track old times for audits
            old_start = slot.start_time

            # Cancel old calendar invite
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

            # Update slot with new times
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
                    detail="Overlapping reschedule slot reservation rejected by exclusion safety checks."
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

                    # Emit billing event
                    from core.workflow_engine import emit_billing_event
                    emit_billing_event(db, interviewer.company_id, "calendar.booking.created", str(slot.id))


                    log_audit_event(
                        db=db,
                        action="schedule.calendar_event_created",
                        actor_type="SYSTEM",
                        company_id=slot.company_id,
                        metadata={"provider": cred.provider, "external_event_id": ext_id}
                    )
                except Exception as cal_err:
                    log_audit_event(
                        db=db,
                        action="schedule.calendar_event_failed",
                        actor_type="SYSTEM",
                        company_id=slot.company_id,
                        metadata={"provider": cred.provider, "error": str(cal_err)}
                    )

            # Log schedule.rescheduled audit event
            log_audit_event(
                db=db,
                action="schedule.rescheduled",
                actor_type="UNAUTHENTICATED",
                company_id=slot.company_id,
                metadata={
                    "interview_id": str(slot.interview_id),
                    "slot_id": str(slot.id),
                    "old_start_time": old_start.isoformat(),
                    "new_start_time": new_start.isoformat()
                }
            )
            db.commit()

        finally:
            release_sync_lock(f"book:{interview.id}")

    return {
        "status": "confirmed",
        "slot_id": str(slot.id),
        "start_time": slot.start_time,
        "end_time": slot.end_time
    }
