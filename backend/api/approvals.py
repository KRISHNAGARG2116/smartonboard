import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func

from api.deps import RequireRecruiter, TenantDb
from models.approval import ApprovalTemplate, ApprovalTemplateStep, ApprovalChain, ApprovalStep
from models.job import Job
from models.offer import Offer
from models.escalation import ApprovalEscalationRule
from schemas.approval import (
    ApprovalTemplateCreate,
    ApprovalTemplateResponse,
    ApprovalChainCreate,
    ApprovalChainResponse,
    ApprovalStepAction,
    ApprovalStepResponse,
    ApprovalEscalationRuleCreate,
    ApprovalEscalationRuleResponse,
)
from core.audit import log_audit_event

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/templates", response_model=ApprovalTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_approval_template(
    db: TenantDb,
    current_user: RequireRecruiter,
    payload: ApprovalTemplateCreate,
):
    """
    Creates a reusable multi-role/user approval workflow template.
    """
    # Create Template
    template = ApprovalTemplate(
        company_id=current_user.company_id,
        name=payload.name,
        description=payload.description,
        target_type=payload.target_type,
        is_active=True,
    )
    db.add(template)
    db.flush()  # get template.id

    # Create Steps
    for step_data in payload.steps:
        step = ApprovalTemplateStep(
            company_id=current_user.company_id,
            approval_template_id=template.id,
            sequence=step_data.sequence,
            parallel_group=step_data.parallel_group,
            role_required=step_data.role_required,
            approver_id=step_data.approver_id,
        )
        db.add(step)

    db.commit()
    db.refresh(template)

    # Log audit event
    log_audit_event(
        db=db,
        action="approval.template_created",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="approval_template",
        resource_id=str(template.id),
        metadata={"name": template.name, "target_type": template.target_type},
    )

    return template


@router.post("/chains", response_model=ApprovalChainResponse, status_code=status.HTTP_201_CREATED)
def instantiate_approval_chain(
    db: TenantDb,
    current_user: RequireRecruiter,
    payload: ApprovalChainCreate,
):
    """
    Starts an active approval chain targeting a requisition or offer, populating steps from the corresponding template.
    """
    # 1. Target integrity validation (checked before insertion to prevent CHECK constraint failures)
    if payload.target_type == "requisition":
        if not payload.job_id or payload.offer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A requisition approval chain must have a job_id and no offer_id",
            )
        # Verify job tenant
        job = db.scalar(
            select(Job).where(
                Job.id == payload.job_id,
                Job.company_id == current_user.company_id
            )
        )
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job requisition not found")
    else:  # offer
        if not payload.offer_id or payload.job_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An offer approval chain must have an offer_id and no job_id",
            )
        # Verify offer tenant
        offer = db.scalar(
            select(Offer).where(
                Offer.id == payload.offer_id,
                Offer.company_id == current_user.company_id
            )
        )
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate offer not found")

    # 2. Fetch approval template and verify tenant
    if not payload.approval_template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="approval_template_id is required to instantiate a chain",
        )
    template = db.scalar(
        select(ApprovalTemplate).where(
            ApprovalTemplate.id == payload.approval_template_id,
            ApprovalTemplate.company_id == current_user.company_id,
            ApprovalTemplate.is_active == True
        )
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval template not found")

    # Verify target type matches template
    if template.target_type != payload.target_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template target type '{template.target_type}' does not match requested target type '{payload.target_type}'",
        )

    # 3. Create active chain
    chain = ApprovalChain(
        company_id=current_user.company_id,
        approval_template_id=template.id,
        target_type=payload.target_type,
        job_id=payload.job_id,
        offer_id=payload.offer_id,
        status="pending",
        current_step_sequence=1,
    )
    db.add(chain)
    db.flush()

    # 4. Copy steps
    t_steps = db.scalars(
        select(ApprovalTemplateStep).where(
            ApprovalTemplateStep.approval_template_id == template.id
        ).order_by(ApprovalTemplateStep.sequence)
    ).all()

    for idx, t_step in enumerate(t_steps):
        # The first sequence step group starts as 'pending', subsequent steps start as 'skipped' or 'pending' later
        initial_status = "pending" if t_step.sequence == 1 else "pending"  # we will keep pending, but track current sequence
        step = ApprovalStep(
            company_id=current_user.company_id,
            approval_chain_id=chain.id,
            sequence=t_step.sequence,
            parallel_group=t_step.parallel_group,
            role_required=t_step.role_required,
            approver_id=t_step.approver_id,
            status=initial_status,
        )
        db.add(step)

    db.commit()
    db.refresh(chain)

    # Log audit event
    log_audit_event(
        db=db,
        action="approval.chain_started",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="approval_chain",
        resource_id=str(chain.id),
        metadata={
            "target_type": chain.target_type,
            "job_id": str(chain.job_id) if chain.job_id else None,
            "offer_id": str(chain.offer_id) if chain.offer_id else None,
        },
    )

    return chain


@router.post("/steps/{step_id}/action", response_model=ApprovalStepResponse)
def action_approval_step(
    db: TenantDb,
    current_user: RequireRecruiter,
    step_id: uuid.UUID,
    payload: ApprovalStepAction,
):
    """
    Approves or rejects a step inside a active approval chain, handling parallel and sequential progression.
    """
    # 1. Fetch step and verify company boundaries
    step = db.scalar(
        select(ApprovalStep).where(
            ApprovalStep.id == step_id,
            ApprovalStep.company_id == current_user.company_id
        )
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval step not found")

    chain = db.scalar(
        select(ApprovalChain).where(
            ApprovalChain.id == step.approval_chain_id,
            ApprovalChain.company_id == current_user.company_id
        )
    )
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval chain not found")

    # 2. Check if the step is active and part of the current sequence group
    if chain.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot action step. Chain is already '{chain.status}'",
        )

    if step.sequence != chain.current_step_sequence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot action step in sequence {step.sequence}. Current pending sequence is {chain.current_step_sequence}",
        )

    if step.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Step is already actioned with status '{step.status}'",
        )

    # 3. Verify user authorization (approver_id matches, or user role matches)
    is_authorized = False
    if step.approver_id and step.approver_id == current_user.id:
        is_authorized = True
    elif step.role_required and current_user.role == step.role_required:
        is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to action this approval step",
        )

    # 4. Process Action
    if payload.action == "reject":
        step.status = "rejected"
        step.actioned_by = current_user.id
        step.actioned_at = datetime.utcnow()
        step.rejection_reason = payload.rejection_reason

        chain.status = "rejected"
        db.commit()

        # Log audit event
        log_audit_event(
            db=db,
            action="approval.step_rejected",
            actor_type="user",
            company_id=current_user.company_id,
            actor_id=current_user.id,
            resource_type="approval_step",
            resource_id=str(step.id),
            metadata={"chain_id": str(chain.id), "reason": payload.rejection_reason},
        )

        return step

    # payload.action == "approve"
    step.status = "approved"
    step.actioned_by = current_user.id
    step.actioned_at = datetime.utcnow()
    db.flush()

    # Log audit event for step approval
    log_audit_event(
        db=db,
        action="approval.step_approved",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="approval_step",
        resource_id=str(step.id),
        metadata={"chain_id": str(chain.id)},
    )

    # Check if other steps inside the current sequence group remain pending
    pending_steps = db.scalar(
        select(func.count(ApprovalStep.id)).where(
            ApprovalStep.approval_chain_id == chain.id,
            ApprovalStep.sequence == step.sequence,
            ApprovalStep.status == "pending"
        )
    )

    if pending_steps == 0:
        # All parallel steps in this sequence are approved!
        # Check if next sequence index exists
        next_step_seq = db.scalar(
            select(ApprovalStep.sequence).where(
                ApprovalStep.approval_chain_id == chain.id,
                ApprovalStep.sequence > step.sequence
            ).order_by(ApprovalStep.sequence.asc()).limit(1)
        )

        if next_step_seq:
            # Advance chain sequence pointer
            chain.current_step_sequence = next_step_seq
        else:
            # No more steps left! Complete the chain!
            chain.status = "approved"
            
            # Log chain completion
            log_audit_event(
                db=db,
                action="approval.chain_completed",
                actor_type="system",
                company_id=current_user.company_id,
                actor_id=None,
                resource_type="approval_chain",
                resource_id=str(chain.id),
                metadata={"status": "approved"},
            )

    db.commit()
    db.refresh(step)
    return step


@router.post("/templates/steps/{step_id}/escalation", response_model=ApprovalEscalationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_approval_escalation_rule(
    db: TenantDb,
    current_user: RequireRecruiter,
    step_id: uuid.UUID,
    payload: ApprovalEscalationRuleCreate,
):
    """
    Configures a timeout escalation rule on an approval template step definition.
    """
    # 1. Fetch template step and verify company boundaries
    step = db.scalar(
        select(ApprovalTemplateStep).where(
            ApprovalTemplateStep.id == step_id,
            ApprovalTemplateStep.company_id == current_user.company_id
        )
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval template step not found")

    # 2. Check if delegate_id (if delegate) exists in the company
    if payload.escalation_type == "delegate":
        if not payload.delegate_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="delegate_id is required when escalation_type is 'delegate'",
            )
        from models.user import User
        delegate = db.scalar(
            select(User).where(
                User.id == payload.delegate_id,
                User.company_id == current_user.company_id
            )
        )
        if not delegate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delegate user not found")

    # 3. Create or Update Rule
    rule = db.scalar(
        select(ApprovalEscalationRule).where(
            ApprovalEscalationRule.approval_template_step_id == step_id,
            ApprovalEscalationRule.company_id == current_user.company_id
        )
    )
    if rule:
        rule.timeout_seconds = payload.timeout_seconds
        rule.escalation_type = payload.escalation_type
        rule.delegate_id = payload.delegate_id
    else:
        rule = ApprovalEscalationRule(
            company_id=current_user.company_id,
            approval_template_step_id=step_id,
            timeout_seconds=payload.timeout_seconds,
            escalation_type=payload.escalation_type,
            delegate_id=payload.delegate_id
        )
        db.add(rule)

    db.commit()
    db.refresh(rule)

    # Log audit event
    log_audit_event(
        db=db,
        action="approval.escalation_configured",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="approval_escalation_rule",
        resource_id=str(rule.id),
        metadata={"approval_template_step_id": str(step_id), "escalation_type": payload.escalation_type},
    )

    return rule
