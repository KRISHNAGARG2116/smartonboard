import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb
from models import Application, User
from models.enums import UserRole, ApplicationStatus
from models.committee import (
    ScorecardTemplate,
    ScorecardTemplateSkill,
    HiringCommittee,
    HiringCommitteeMember,
    CommitteeReview,
    CommitteeReviewReviewer,
)
from schemas.committee import (
    ScorecardTemplateCreate,
    ScorecardTemplateResponse,
    CommitteeCreate,
    CommitteeResponse,
    ReviewInitiate,
    CommitteeReviewResponse,
    ReviewReconcile,
)
from core.audit import log_audit_event

router = APIRouter(tags=["committees"])

# --- Scorecard Templates ---

@router.post("/scorecards/templates", response_model=ScorecardTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_scorecard_template(
    db: TenantDb,
    current_user: RequireRecruiter,
    payload: ScorecardTemplateCreate,
):
    """
    Creates a new Scorecard Template with specific skill grading keys and weights.
    The sum of weights is validated to equal exactly 1.0.
    """
    template = ScorecardTemplate(
        company_id=current_user.company_id,
        name=payload.name,
        description=payload.description,
        is_active=True
    )
    db.add(template)
    db.flush()

    for skill in payload.skills:
        s_skill = ScorecardTemplateSkill(
            company_id=current_user.company_id,
            scorecard_template_id=template.id,
            skill_key=skill.skill_key,
            display_name=skill.display_name,
            weight=skill.weight
        )
        db.add(s_skill)

    db.commit()
    db.refresh(template)

    # Log audit event
    log_audit_event(
        db=db,
        action="scorecard.template_created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="scorecard_templates",
        resource_id=str(template.id),
        metadata={"name": template.name}
    )

    return template


@router.get("/scorecards/templates/{template_id}", response_model=ScorecardTemplateResponse)
def get_scorecard_template(
    template_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    template = db.scalar(
        select(ScorecardTemplate).where(
            ScorecardTemplate.id == template_id,
            ScorecardTemplate.company_id == current_user.company_id
        )
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard template not found")
    return template


# --- Hiring Committees ---

@router.post("/committees", response_model=CommitteeResponse, status_code=status.HTTP_201_CREATED)
def create_hiring_committee(
    db: TenantDb,
    current_user: RequireRecruiter,
    payload: CommitteeCreate,
):
    """
    Registers a hiring committee, assign member weights, and sets veto skill checks.
    """
    committee = HiringCommittee(
        company_id=current_user.company_id,
        name=payload.name,
        description=payload.description,
        quorum_percentage=payload.quorum_percentage,
        min_score_threshold=payload.min_score_threshold,
        consensus_sd_threshold=payload.consensus_sd_threshold,
        allow_veto=payload.allow_veto,
        veto_skill_keys=payload.veto_skill_keys
    )
    db.add(committee)
    db.flush()

    for member in payload.members:
        # Verify user belongs to same company
        user = db.scalar(
            select(User).where(
                User.id == member.user_id,
                User.company_id == current_user.company_id
            )
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {member.user_id} does not exist in this company"
            )

        c_member = HiringCommitteeMember(
            company_id=current_user.company_id,
            hiring_committee_id=committee.id,
            user_id=member.user_id,
            role=member.role,
            reviewer_weight=member.reviewer_weight
        )
        db.add(c_member)

    db.commit()
    db.refresh(committee)

    log_audit_event(
        db=db,
        action="committee.created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="hiring_committees",
        resource_id=str(committee.id),
        metadata={"name": committee.name}
    )

    return committee


@router.get("/committees/{committee_id}", response_model=CommitteeResponse)
def get_hiring_committee(
    committee_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    committee = db.scalar(
        select(HiringCommittee).where(
            HiringCommittee.id == committee_id,
            HiringCommittee.company_id == current_user.company_id
        )
    )
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hiring committee not found")
    return committee


# --- Committee Reviews ---

@router.post("/applications/{application_id}/reviews/initiate", response_model=CommitteeReviewResponse, status_code=status.HTTP_201_CREATED)
def initiate_committee_review(
    application_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
    payload: ReviewInitiate,
):
    """
    Starts a committee review cycle for a candidate. Snapshots the reviewer roster,
    weights, and roles immutably to lock the reviewers group for this candidate.
    """
    # 1. Fetch Application
    app_record = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 2. Fetch Hiring Committee & Roster
    committee = db.scalar(
        select(HiringCommittee).where(
            HiringCommittee.id == payload.hiring_committee_id,
            HiringCommittee.company_id == current_user.company_id
        )
    )
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hiring committee not found")

    # Verify template exists
    template = db.scalar(
        select(ScorecardTemplate).where(
            ScorecardTemplate.id == payload.scorecard_template_id,
            ScorecardTemplate.company_id == current_user.company_id
        )
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard template not found")

    # 3. Create Committee Review Record
    review = CommitteeReview(
        company_id=current_user.company_id,
        application_id=application_id,
        hiring_committee_id=payload.hiring_committee_id,
        scorecard_template_id=payload.scorecard_template_id,
        status="pending",
        review_due_at=payload.review_due_at
    )
    db.add(review)
    db.flush()

    # 4. Snapshot active committee members immutably (Refinement 2)
    members = db.scalars(
        select(HiringCommitteeMember).where(
            HiringCommitteeMember.hiring_committee_id == committee.id
        )
    ).all()

    if not members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot initiate review: designated committee has no active members"
        )

    for m in members:
        snap_reviewer = CommitteeReviewReviewer(
            company_id=current_user.company_id,
            committee_review_id=review.id,
            user_id=m.user_id,
            role=m.role,
            reviewer_weight=m.reviewer_weight
        )
        db.add(snap_reviewer)

    # Update application status to trace committee tracking
    app_record.committee_status = "pending"

    db.commit()
    db.refresh(review)

    log_audit_event(
        db=db,
        action="committee.review_initiated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="committee_reviews",
        resource_id=str(review.id),
        metadata={
            "application_id": str(application_id),
            "hiring_committee_id": str(committee.id),
            "review_due_at": review.review_due_at.isoformat() if review.review_due_at else None
        }
    )

    return review


@router.get("/reviews/{review_id}", response_model=CommitteeReviewResponse)
def get_committee_review(
    review_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    review = db.scalar(
        select(CommitteeReview).where(
            CommitteeReview.id == review_id,
            CommitteeReview.company_id == current_user.company_id
        )
    )
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Committee review not found")
    return review


@router.post("/reviews/{review_id}/reconcile", response_model=CommitteeReviewResponse)

def reconcile_disputed_review(
    review_id: uuid.UUID,
    payload: ReviewReconcile,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Allows the Committee Chair OR Tenant Owner to manually reconcile a disputed review,
    entering justification notes and overriding consensus status to aligned_approve or aligned_reject.
    """
    review = db.scalar(
        select(CommitteeReview).where(
            CommitteeReview.id == review_id,
            CommitteeReview.company_id == current_user.company_id
        )
    )
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Committee review not found")

    if review.status != "disputed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only reviews in 'disputed' status can be reconciled. Current status: '{review.status}'"
        )

    # 1. Authorize: Committee Chair OR Tenant Owner (Refinement 4)
    is_authorized = current_user.role == UserRole.OWNER

    if not is_authorized:
        # Check snapshot for Chair role
        is_chair = db.scalar(
            select(CommitteeReviewReviewer).where(
                CommitteeReviewReviewer.committee_review_id == review_id,
                CommitteeReviewReviewer.user_id == current_user.id,
                CommitteeReviewReviewer.role == "chair"
            )
        )
        if is_chair:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the designated Committee Chair or a Tenant Owner may reconcile disputes"
        )

    # 2. Update Resolution
    resolution = payload.resolution
    review.reconciliation_notes = payload.notes
    review.resolved_at = datetime.now(timezone.utc)

    from core.consensus import trigger_offer_recommendation_pipeline

    if resolution == "approve":
        review.status = "aligned_approve"
        db.flush()
        # Trigger offer recom chain
        trigger_offer_recommendation_pipeline(db, review)
    else:
        review.status = "aligned_reject"
        db.flush()

        app = db.get(Application, review.application_id)
        if app:
            app.status = ApplicationStatus.REJECTED
            app.committee_status = "aligned_reject"
            db.flush()

        log_audit_event(
            db=db,
            action="committee.review_resolved",
            actor_type="RECRUITER",
            actor_id=current_user.id,
            company_id=review.company_id,
            resource_type="committee_review",
            resource_id=str(review.id),
            metadata={"status": "aligned_reject", "is_reconciled": True, "reconciled_by": str(current_user.id)}
        )

    # Sync application committee status
    app = db.get(Application, review.application_id)
    if app:
        app.committee_status = review.status
        db.flush()

    # Log reconcile audit event
    log_audit_event(
        db=db,
        action="committee.review_reconciled",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=review.company_id,
        resource_type="committee_review",
        resource_id=str(review.id),
        metadata={
            "resolution": resolution,
            "reconciliation_notes": payload.notes,
            "actor_role": current_user.role.value
        }
    )

    db.commit()
    db.refresh(review)
    return review
