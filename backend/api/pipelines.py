import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb
from models.pipeline import PipelineTemplate, Pipeline, StageDefinition
from models.job import Job
from schemas.pipeline import (
    PipelineTemplateCreate,
    PipelineTemplateResponse,
    PipelineResponse,
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
