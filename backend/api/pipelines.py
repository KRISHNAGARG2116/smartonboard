import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb
from models.pipeline import PipelineTemplate, Pipeline, StageDefinition
from models.job import Job
from models.sla import StageSLA
from schemas.pipeline import (
    PipelineTemplateCreate,
    PipelineTemplateResponse,
    PipelineResponse,
    StageSLACreate,
    StageSLAResponse,
)
from core.audit import log_audit_event

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("/templates", response_model=PipelineTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline_template(
    db: TenantDb,
    current_user: RequireRecruiter,
    payload: PipelineTemplateCreate,
):
    """
    Creates a reusable hiring pipeline template and sequential stage definitions.
    """
    # Create Template
    template = PipelineTemplate(
        company_id=current_user.company_id,
        name=payload.name,
        description=payload.description,
        is_active=True,
    )
    db.add(template)
    db.flush()  # get template.id

    # Create stage definitions
    for stage_data in payload.stages:
        stage = StageDefinition(
            company_id=current_user.company_id,
            pipeline_template_id=template.id,
            name=stage_data.name,
            sequence=stage_data.sequence,
            base_category=stage_data.base_category,
            settings=stage_data.settings,
            automation_rules=[rule.model_dump() for rule in stage_data.automation_rules],
            is_active=True,
        )
        db.add(stage)

    db.commit()
    db.refresh(template)

    # Log audit event
    log_audit_event(
        db=db,
        action="pipeline.template_created",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="pipeline_template",
        resource_id=str(template.id),
        metadata={"name": template.name},
    )

    return template


@router.post("/jobs/{job_id}/pipeline", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def instantiate_pipeline_from_template(
    db: TenantDb,
    current_user: RequireRecruiter,
    job_id: uuid.UUID,
    template_id: uuid.UUID = Query(..., description="The template ID to clone"),
):
    """
    Clones all stage definitions from a pipeline template and instantiates a
    job-specific dynamic pipeline, protecting the job from downstream template changes.
    """
    # 1. Fetch job and verify tenant boundary
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # 2. Fetch template and verify tenant boundary
    template = db.scalar(
        select(PipelineTemplate).where(
            PipelineTemplate.id == template_id,
            PipelineTemplate.company_id == current_user.company_id,
            PipelineTemplate.is_active == True
        )
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline template not found")

    # 3. Create Pipeline Instance
    pipeline = Pipeline(
        company_id=current_user.company_id,
        name=f"Pipeline - {job.title}",
        description=f"Cloned from template: {template.name}",
        pipeline_version=1,
    )
    db.add(pipeline)
    db.flush()

    # 4. Clone all active stages
    stages = db.scalars(
        select(StageDefinition).where(
            StageDefinition.pipeline_template_id == template.id,
            StageDefinition.is_active == True
        ).order_by(StageDefinition.sequence)
    ).all()

    for idx, t_stage in enumerate(stages, start=1):
        stage = StageDefinition(
            company_id=current_user.company_id,
            pipeline_id=pipeline.id,
            name=t_stage.name,
            sequence=idx,
            base_category=t_stage.base_category,
            settings=t_stage.settings,
            automation_rules=t_stage.automation_rules,
            is_active=True,
        )
        db.add(stage)

    db.commit()
    db.refresh(pipeline)

    # Log audit event
    log_audit_event(
        db=db,
        action="pipeline.bound_to_job",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="pipeline",
        resource_id=str(pipeline.id),
        metadata={"job_id": str(job_id), "template_id": str(template_id)},
    )

    return pipeline


@router.post("/stages/{stage_id}/sla", response_model=StageSLAResponse, status_code=status.HTTP_201_CREATED)
def create_stage_sla(
    db: TenantDb,
    current_user: RequireRecruiter,
    stage_id: uuid.UUID,
    payload: StageSLACreate,
):
    """
    Registers a time limit SLA on a stage definition, enforcing the approved validation:
    - fallback_stage_id (if provided) must belong to the exact same pipeline template or pipeline instance as the source stage.
    """
    # 1. Fetch source stage
    stage = db.scalar(
        select(StageDefinition).where(
            StageDefinition.id == stage_id,
            StageDefinition.company_id == current_user.company_id
        )
    )
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage definition not found")

    # 2. Validation: check fallback_stage_id belongs to the same pipeline version as source stage
    if payload.fallback_stage_id:
        fallback = db.scalar(
            select(StageDefinition).where(
                StageDefinition.id == payload.fallback_stage_id,
                StageDefinition.company_id == current_user.company_id
            )
        )
        if not fallback:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fallback stage definition not found")

        # Verify pipeline templates or pipeline instances match exactly!
        if stage.pipeline_template_id != fallback.pipeline_template_id or stage.pipeline_id != fallback.pipeline_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fallback stage must belong to the same pipeline or template version as the source stage"
            )

    # 3. Create SLA (overwrite if exists or simple create)
    sla = db.scalar(
        select(StageSLA).where(
            StageSLA.stage_definition_id == stage_id,
            StageSLA.company_id == current_user.company_id
        )
    )
    if sla:
        sla.duration_seconds = payload.duration_seconds
        sla.escalation_action = payload.escalation_action
        sla.fallback_stage_id = payload.fallback_stage_id
    else:
        sla = StageSLA(
            company_id=current_user.company_id,
            stage_definition_id=stage_id,
            duration_seconds=payload.duration_seconds,
            escalation_action=payload.escalation_action,
            fallback_stage_id=payload.fallback_stage_id
        )
        db.add(sla)

    db.commit()
    db.refresh(sla)

    # Log audit event
    log_audit_event(
        db=db,
        action="pipeline.stage_sla_configured",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="stage_sla",
        resource_id=str(sla.id),
        metadata={"stage_definition_id": str(stage_id), "duration_seconds": payload.duration_seconds},
    )

    return sla
