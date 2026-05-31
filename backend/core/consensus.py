import logging
import math
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.application import Application
from models.scorecard import Scorecard
from models.approval import ApprovalTemplate, ApprovalTemplateStep, ApprovalChain, ApprovalStep
from models.committee import CommitteeReview, CommitteeReviewReviewer, ScorecardTemplateSkill
from models.enums import ApplicationStatus
from core.audit import log_audit_event

logger = logging.getLogger(__name__)

def calculate_scorecard_weighted_score(db: Session, scorecard: Scorecard, template_id: uuid.UUID) -> float | None:
    """
    Calculates and updates a scorecard's weighted score based on a scorecard template's skills and weights.
    """
    skills = db.scalars(
        select(ScorecardTemplateSkill).where(ScorecardTemplateSkill.scorecard_template_id == template_id)
    ).all()
    if not skills:
        return None

    weighted_score = 0.0
    for skill in skills:
        # Fetch grader's score for this skill key from JSONB
        score_val = scorecard.criteria_scores.get(skill.skill_key)
        if score_val is not None:
            weighted_score += float(score_val) * float(skill.weight)
        else:
            # Fallback if a key is missing
            pass

    scorecard.weighted_score = weighted_score
    db.flush()
    return weighted_score


def evaluate_committee_review_consensus(db: Session, review_id: uuid.UUID) -> CommitteeReview:
    """
    Executes the automated consensus engine on an active committee review:
    1. Checks Quorum based on snapshotted reviewers.
    2. Performs dynamic reviewer weights normalization.
    3. Calculates overall normalized candidate weighted score.
    4. Computes custom standard deviation and compares against threshold.
    5. Enforces configurable category-based vetos.
    6. Triggers automated workflow handoffs (spawns offer approval chains).
    """
    review = db.scalar(
        select(CommitteeReview).where(CommitteeReview.id == review_id)
    )
    if not review or review.status in ("aligned_approve", "aligned_reject", "resolved"):
        return review

    committee = review.committee
    if not committee:
        return review

    # Fetch snapshotted reviewers
    snap_reviewers = db.scalars(
        select(CommitteeReviewReviewer).where(CommitteeReviewReviewer.committee_review_id == review_id)
    ).all()
    if not snap_reviewers:
        return review

    active_count = len(snap_reviewers)
    reviewer_map = {r.user_id: r for r in snap_reviewers}

    # Fetch submitted scorecards for this review
    scorecards = db.scalars(
        select(Scorecard).where(Scorecard.committee_review_id == review_id)
    ).all()

    # Filter scorecards to only those submitted by snapshotted reviewers
    valid_scorecards = []
    for sc in scorecards:
        if sc.grader_id in reviewer_map:
            # Ensure scorecard weighted score is calculated
            calculate_scorecard_weighted_score(db, sc, review.scorecard_template_id)
            valid_scorecards.append(sc)

    submitted_count = len(valid_scorecards)

    # 1. Quorum Check
    quorum_percentage = committee.quorum_percentage
    submission_rate = (submitted_count / active_count) * 100 if active_count > 0 else 0.0

    if submission_rate < quorum_percentage:
        review.status = "pending"
        db.flush()
        return review

    # 2. Reviewer Weights Normalization & Overall Weighted Score
    # Retrieve snapshotted weights for submitted reviewers
    weights = []
    scores = []
    for sc in valid_scorecards:
        reviewer = reviewer_map[sc.grader_id]
        weights.append(float(reviewer.reviewer_weight))
        scores.append(float(sc.weighted_score or 0.0))

    total_weight = sum(weights)
    if total_weight <= 0:
        total_weight = 1.0
        weights = [1.0 for _ in weights]

    # Calculate overall weighted average score
    overall_score = sum(score * (weight / total_weight) for score, weight in zip(scores, weights))
    review.average_score = overall_score

    # 3. Compute Standard Deviation (sigma)
    variance = sum((score - overall_score) ** 2 for score in scores) / submitted_count
    sigma = math.sqrt(variance)

    # 4. Veto Checks
    veto_triggered = False
    if committee.allow_veto and committee.veto_skill_keys:
        veto_keys = set(committee.veto_skill_keys)
        for sc in valid_scorecards:
            for key, score_val in sc.criteria_scores.items():
                if key in veto_keys and int(score_val) == 1:
                    veto_triggered = True
                    break
            if veto_triggered:
                break

    # 5. Log consensus event
    log_audit_event(
        db=db,
        action="committee.consensus_calculated",
        actor_type="system",
        company_id=review.company_id,
        resource_type="committee_review",
        resource_id=str(review_id),
        metadata={
            "overall_score": overall_score,
            "standard_deviation": sigma,
            "veto_triggered": veto_triggered,
            "submitted_count": submitted_count,
        }
    )

    # 6. Apply Alignment Thresholds
    sd_threshold = float(committee.consensus_sd_threshold)
    min_score = float(committee.min_score_threshold)

    if veto_triggered or sigma >= sd_threshold:
        # Trigger dispute state
        review.status = "disputed"
        db.flush()

        log_audit_event(
            db=db,
            action="committee.review_disputed",
            actor_type="system",
            company_id=review.company_id,
            resource_type="committee_review",
            resource_id=str(review_id),
            metadata={
                "reason": "Veto Triggered" if veto_triggered else f"SD {sigma:.2f} exceeded threshold {sd_threshold:.2f}",
                "overall_score": overall_score
            }
        )
    else:
        # Cleanly aligned
        if overall_score >= min_score:
            review.status = "aligned_approve"
            review.resolved_at = datetime.now(timezone.utc)
            db.flush()
            
            # Execute approval trigger
            trigger_offer_recommendation_pipeline(db, review)
        else:
            review.status = "aligned_reject"
            review.resolved_at = datetime.now(timezone.utc)
            db.flush()

            # Transition application to rejected
            app = db.get(Application, review.application_id)
            if app:
                app.status = ApplicationStatus.REJECTED
                app.committee_status = "aligned_reject"
                db.flush()

            log_audit_event(
                db=db,
                action="committee.review_resolved",
                actor_type="system",
                company_id=review.company_id,
                resource_type="committee_review",
                resource_id=str(review_id),
                metadata={"status": "aligned_reject", "overall_score": overall_score}
            )

    # Sync application committee status
    app = db.get(Application, review.application_id)
    if app:
        app.committee_status = review.status
        db.flush()

    db.commit()
    db.refresh(review)
    return review


def trigger_offer_recommendation_pipeline(db: Session, review: CommitteeReview):
    """
    Executes automated offer recommendation pipeline handoff:
    1. Transitions application to approved.
    2. Instantiates offer Approval Chain if a template is registered.
    3. Logs committee.offer_chain_created compliance audit event.
    """
    # 1. Update application status
    app = db.get(Application, review.application_id)
    if not app:
        return

    app.status = ApplicationStatus.OFFER
    app.committee_status = review.status
    db.flush()

    log_audit_event(
        db=db,
        action="committee.review_resolved",
        actor_type="system",
        company_id=review.company_id,
        resource_type="committee_review",
        resource_id=str(review.id),
        metadata={"status": "aligned_approve", "overall_score": float(review.average_score or 0.0)}
    )

    # 2. Check for active offer Approval Template
    template = db.scalar(
        select(ApprovalTemplate).where(
            ApprovalTemplate.company_id == review.company_id,
            ApprovalTemplate.target_type == "offer",
            ApprovalTemplate.is_active == True
        )
    )
    if not template:
        logger.info(f"No active offer approval template registered for company {review.company_id}. Skipping chain creation.")
        return

    # Link to application's offer if exists, or create offer stub
    from models.offer import Offer
    offer = db.scalar(select(Offer).where(Offer.application_id == app.id))
    if not offer:
        from datetime import date, timedelta
        offer = Offer(
            company_id=review.company_id,
            application_id=app.id,
            status="draft",
            salary=0.00,
            start_date=date.today() + timedelta(days=30),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.add(offer)
        db.flush()

    # 3. Instantiate Approval Chain with offer_id directly to satisfy check constraint
    chain = ApprovalChain(
        company_id=review.company_id,
        approval_template_id=template.id,
        target_type="offer",
        offer_id=offer.id,
        status="pending",
        current_step_sequence=1
    )
    db.add(chain)
    db.flush()

    # Clone template steps
    t_steps = db.scalars(
        select(ApprovalTemplateStep).where(
            ApprovalTemplateStep.approval_template_id == template.id
        ).order_by(ApprovalTemplateStep.sequence)
    ).all()

    for ts in t_steps:
        step = ApprovalStep(
            company_id=review.company_id,
            approval_chain_id=chain.id,
            sequence=ts.sequence,
            parallel_group=ts.parallel_group,
            role_required=ts.role_required,
            approver_id=ts.approver_id,
            status="pending"
        )
        db.add(step)

    db.flush()

    # Emit committee.offer_chain_created compliance audit event
    log_audit_event(
        db=db,
        action="committee.offer_chain_created",
        actor_type="system",
        company_id=review.company_id,
        resource_type="approval_chain",
        resource_id=str(chain.id),
        metadata={
            "committee_review_id": str(review.id),
            "application_id": str(app.id),
            "offer_id": str(offer.id),
            "template_id": str(template.id)
        }
    )
    db.flush()
