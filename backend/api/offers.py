import uuid
from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select

from api.deps import RequireRecruiter, RequireOwner, TenantDb
from models import Application, Offer
from models.enums import ApplicationStatus
from celery_worker import (
    track_stage_transition_async,
    track_recruiter_productivity_async,
)
from schemas.offer import (
    OfferCreateRequest,
    OfferDecideRequest,
    OfferResponse,
    OnboardingTriggerPayload,
)
from core.audit import log_audit_event

router = APIRouter(prefix="/applications/{application_id}/offers", tags=["offers"])


def _get_application(application_id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter) -> Application:
    app_record = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app_record


def _get_offer(application_id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter) -> Offer:
    offer = db.scalar(
        select(Offer).where(
            Offer.application_id == application_id,
            Offer.company_id == current_user.company_id
        )
    )
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    return offer


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    application_id: uuid.UUID,
    body: OfferCreateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    # 1. Enforce One Application -> One Offer UNIQUE constraint check
    existing = db.scalar(select(Offer).where(Offer.application_id == application_id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An offer already exists for this application. Revisions are not supported."
        )

    # 2. Enforce Application Status check (Must be INTERVIEW)
    if app_record.status != ApplicationStatus.INTERVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create offer. Application must be in INTERVIEW stage. Current stage: {app_record.status.value.upper()}"
        )

    # 3. Verify expiration date is in the future
    if body.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiration timestamp must be in the future"
        )

    # 4. Insert Offer draft
    offer = Offer(
        company_id=current_user.company_id,
        application_id=application_id,
        salary=body.salary,
        equity_grant=body.equity_grant,
        start_date=body.start_date,
        expires_at=body.expires_at,
        status="draft"
    )
    db.add(offer)

    # 5. Automatically transition Application status from INTERVIEW -> OFFER
    previous_status = app_record.status.value
    app_record.status = ApplicationStatus.OFFER
    new_status = ApplicationStatus.OFFER.value

    db.commit()
    db.refresh(offer)
    db.refresh(app_record)

    # Dispatch background tracking tasks
    track_recruiter_productivity_async.delay(
        str(current_user.company_id),
        str(current_user.id),
        "offer_create"
    )
    track_stage_transition_async.delay(
        str(current_user.company_id),
        str(application_id),
        previous_status,
        new_status,
        str(current_user.id)
    )

    # 6. Corrected Audit Metadata for offer.created
    log_audit_event(
        db=db,
        action="offer.created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="offers",
        resource_id=str(offer.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "offer_id": str(offer.id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "application_status_before": previous_status,
            "application_status_after": new_status
        }
    )

    # 7. Log application.status_changed as a separate event
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
            "trigger_event": "offer.created"
        }
    )

    return offer


@router.get("", response_model=OfferResponse)
def get_application_offer(
    application_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    _get_application(application_id, db, current_user)
    return _get_offer(application_id, db, current_user)


@router.get("/{offer_id}", response_model=OfferResponse)
def get_specific_offer(
    application_id: uuid.UUID,
    offer_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    _get_application(application_id, db, current_user)
    offer = db.scalar(
        select(Offer).where(
            Offer.id == offer_id,
            Offer.application_id == application_id,
            Offer.company_id == current_user.company_id
        )
    )
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    return offer


@router.post("/approve", response_model=OfferResponse)
def approve_offer(
    application_id: uuid.UUID,
    request: Request,
    current_user: RequireOwner, # Strictly enforces Owner only!
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)
    offer = _get_offer(application_id, db, current_user)

    # 1. Enforce Terminal State checks
    if offer.status in {"signed", "rejected", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition out of a terminal offer state"
        )

    # 2. Enforce strict draft -> approved transition
    if offer.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition. Expected: DRAFT -> APPROVED. Current status: {offer.status.upper()}"
        )

    offer.status = "approved"
    db.commit()
    db.refresh(offer)

    # Log audit event
    log_audit_event(
        db=db,
        action="offer.approved",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="offers",
        resource_id=str(offer.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "offer_id": str(offer.id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "previous_status": app_record.status.value,
            "new_status": app_record.status.value
        }
    )

    return offer


@router.post("/send", response_model=OfferResponse)
def send_offer(
    application_id: uuid.UUID,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)
    offer = _get_offer(application_id, db, current_user)

    # 1. Enforce Terminal State checks
    if offer.status in {"signed", "rejected", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition out of a terminal offer state"
        )

    # 2. Enforce strict approved -> sent transition
    if offer.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition. Expected: APPROVED -> SENT. Current status: {offer.status.upper()}"
        )

    offer.status = "sent"
    db.commit()
    db.refresh(offer)

    # Log audit event
    log_audit_event(
        db=db,
        action="offer.sent",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="offers",
        resource_id=str(offer.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "offer_id": str(offer.id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "previous_status": app_record.status.value,
            "new_status": app_record.status.value
        }
    )

    return offer


@router.post("/decide", response_model=OfferResponse)
def decide_offer(
    application_id: uuid.UUID,
    body: OfferDecideRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)
    offer = _get_offer(application_id, db, current_user)

    # 1. Enforce Terminal State checks
    if offer.status in {"signed", "rejected", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition out of a terminal offer state"
        )

    # 2. Enforce strict sent -> signed / rejected transition
    if offer.status != "sent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition. Expected transition from SENT. Current status: {offer.status.upper()}"
        )

    previous_app_status = app_record.status.value
    status_changed = False
    onboarding_trigger = None

    if body.decision == "signed":
        # Transition Offer to signed, and Application to hired
        offer.status = "signed"
        app_record.status = ApplicationStatus.HIRED
        status_changed = True
        
        # Generate Onboarding Trigger Payload
        onboarding_trigger = OnboardingTriggerPayload(
            candidate_id=app_record.candidate_id,
            application_id=application_id,
            offer_id=offer.id,
            company_id=current_user.company_id,
            start_date=offer.start_date
        )
        
        db.commit()
        db.refresh(offer)
        db.refresh(app_record)

        # Log offer.signed
        log_audit_event(
            db=db,
            action="offer.signed",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="offers",
            resource_id=str(offer.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "application_id": str(application_id),
                "offer_id": str(offer.id),
                "candidate_id": str(app_record.candidate_id),
                "actor_id": str(current_user.id),
                "previous_status": previous_app_status,
                "new_status": app_record.status.value
            }
        )
    else:
        # Transition Offer to rejected, and Application to rejected
        offer.status = "rejected"
        app_record.status = ApplicationStatus.REJECTED
        status_changed = True

        db.commit()
        db.refresh(offer)
        db.refresh(app_record)

        # Log offer.rejected
        log_audit_event(
            db=db,
            action="offer.rejected",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=current_user.company_id,
            resource_type="offers",
            resource_id=str(offer.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "application_id": str(application_id),
                "offer_id": str(offer.id),
                "candidate_id": str(app_record.candidate_id),
                "actor_id": str(current_user.id),
                "previous_status": previous_app_status,
                "new_status": app_record.status.value
            }
        )

    # Dispatch background tracking tasks
    if status_changed:
        track_stage_transition_async.delay(
            str(current_user.company_id),
            str(application_id),
            previous_app_status,
            app_record.status.value,
            str(current_user.id)
        )
    if body.decision == "signed":
        track_recruiter_productivity_async.delay(
            str(current_user.company_id),
            str(current_user.id),
            "offer_accept"
        )

    # Log separate application.status_changed event
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
                "previous_status": previous_app_status,
                "new_status": app_record.status.value,
                "trigger_event": f"offer.{body.decision}"
            }
        )

    resp = OfferResponse.model_validate(offer)
    if onboarding_trigger:
        resp.onboarding_trigger = onboarding_trigger
    return resp


@router.post("/expire", response_model=OfferResponse)
def expire_offer(
    application_id: uuid.UUID,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)
    offer = _get_offer(application_id, db, current_user)

    # 1. Enforce Terminal State checks
    if offer.status in {"signed", "rejected", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition out of a terminal offer state"
        )

    # 2. Enforce strict sent -> expired transition
    if offer.status != "sent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition. Expected: SENT -> EXPIRED. Current status: {offer.status.upper()}"
        )

    offer.status = "expired"
    db.commit()
    db.refresh(offer)

    # Log audit event
    log_audit_event(
        db=db,
        action="offer.expired",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="offers",
        resource_id=str(offer.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "offer_id": str(offer.id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "previous_status": app_record.status.value,
            "new_status": app_record.status.value
        }
    )

    return offer
