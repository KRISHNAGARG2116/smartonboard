from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import Offer, Application, Candidate
from core.reporting import generate_pdf
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid
import os

router = APIRouter(prefix="/candidate/offers", tags=["candidate-offers"])

class AcceptOfferSchema(BaseModel):
    client_updated_at: datetime

class DeclineOfferSchema(BaseModel):
    decline_reason: str
    client_updated_at: datetime

class ClarifyOfferSchema(BaseModel):
    message: str

@router.get("")
def list_offers(
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    offers = []
    if candidate_ids:
        stmt = select(Offer).join(
            Application, Offer.application_id == Application.id
        ).where(Application.candidate_id.in_(candidate_ids))
        offers = db.scalars(stmt).all()

    return [
        {
            "id": str(o.id),
            "application_id": str(o.application_id),
            "salary": float(o.salary),
            "equity_grant": o.equity_grant,
            "start_date": o.start_date.isoformat(),
            "expires_at": o.expires_at.isoformat(),
            "status": o.status,
            "document_path": o.document_path,
            "decline_reason": o.decline_reason,
            "updated_at": o.updated_at.isoformat()
        }
        for o in offers
    ]

@router.post("/{id}/accept")
def accept_offer(
    id: uuid.UUID,
    body: AcceptOfferSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    offer = None
    if candidate_ids:
        offer = db.scalar(
            select(Offer).join(
                Application, Offer.application_id == Application.id
            ).where(
                Offer.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Idempotency check
    if offer.status == "accepted":
        return {"status": "success", "message": "Offer already accepted"}

    # Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated = offer.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Offer has been modified by another process. Please reload and try again."
                )

    offer.status = "accepted"
    db.add(offer)
    db.commit()

    # Trigger async Celery workflow for onboarding, HRIS triggers, notifications
    from celery_worker import process_offer_acceptance_async
    process_offer_acceptance_async.delay(str(offer.id))

    return {"status": "success", "message": "Offer accepted successfully"}

@router.post("/{id}/decline")
def decline_offer(
    id: uuid.UUID,
    body: DeclineOfferSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    offer = None
    if candidate_ids:
        offer = db.scalar(
            select(Offer).join(
                Application, Offer.application_id == Application.id
            ).where(
                Offer.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Idempotency check
    if offer.status == "declined":
        return {"status": "success", "message": "Offer already declined"}

    # Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated = offer.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Offer has been modified by another process. Please reload and try again."
                )

    offer.status = "declined"
    offer.decline_reason = body.decline_reason
    db.add(offer)
    db.commit()
    return {"status": "success", "message": "Offer declined"}

@router.post("/{id}/clarify")
def clarify_offer(
    id: uuid.UUID,
    body: ClarifyOfferSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    offer = None
    if candidate_ids:
        offer = db.scalar(
            select(Offer).join(
                Application, Offer.application_id == Application.id
            ).where(
                Offer.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # In a full flow, this would log a notification or message for the recruiter.
    # We will log an audit log or create a CandidateMessage thread.
    return {"status": "success", "message": "Clarification request submitted"}

@router.get("/{id}/download")
def download_offer_pdf(
    id: uuid.UUID,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    offer = None
    if candidate_ids:
        offer = db.scalar(
            select(Offer).join(
                Application, Offer.application_id == Application.id
            ).where(
                Offer.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Generate PDF bytes dynamically
    rows = [
        {"Component": "Base Salary", "Value": f"${offer.salary:,.2f}"},
        {"Component": "Equity Grant", "Value": offer.equity_grant or "None"},
        {"Component": "Start Date", "Value": offer.start_date.isoformat()},
        {"Component": "Offer Expiration", "Value": offer.expires_at.isoformat()}
    ]

    pdf_bytes = generate_pdf(
        report_title="OFFER OF EMPLOYMENT",
        headers=["Component", "Value"],
        rows=rows,
        company_name="SmartOnboard"
    )

    # Save to storage path if not already present
    storage_dir = "storage/offers"
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, f"{str(offer.id)}.pdf")
    
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    offer.document_path = file_path
    db.add(offer)
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=offer_{str(offer.id)}.pdf"}
    )
