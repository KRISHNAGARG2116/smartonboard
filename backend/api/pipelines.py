import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, delete

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
    PipelineUpdate,
    PipelineDetailsResponse,
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

    job.pipeline_id = pipeline.id
    db.flush()

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

    db.commit()
    db.refresh(pipeline)
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


@router.get("/templates", response_model=list[PipelineTemplateResponse])
def list_pipeline_templates(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Lists all reusable pipeline templates.
    """
    templates = db.scalars(
        select(PipelineTemplate).where(
            PipelineTemplate.company_id == current_user.company_id,
            PipelineTemplate.is_active == True
        )
    ).all()
    return templates


@router.get("/jobs/{job_id}/pipeline", response_model=PipelineDetailsResponse)
def get_job_pipeline(
    db: TenantDb,
    current_user: RequireRecruiter,
    job_id: uuid.UUID,
):
    """
    Returns the instantiated pipeline with its active StageDefinitions for the job.
    """
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not job.pipeline_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job does not have an active pipeline")

    pipeline = db.scalar(
        select(Pipeline).where(
            Pipeline.id == job.pipeline_id,
            Pipeline.company_id == current_user.company_id
        )
    )
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    stages = db.scalars(
        select(StageDefinition).where(
            StageDefinition.pipeline_id == pipeline.id,
            StageDefinition.is_active == True
        ).order_by(StageDefinition.sequence)
    ).all()
    pipeline.stages = stages
    return pipeline


@router.put("/jobs/{job_id}/pipeline", response_model=PipelineDetailsResponse)
def update_job_pipeline(
    db: TenantDb,
    current_user: RequireRecruiter,
    job_id: uuid.UUID,
    payload: PipelineUpdate,
):
    """
    Customizes the stage definitions of a job pipeline. If candidates are actively
    moving through the current version, increments version and clones new StageDefinitions
    so that active applications stay bound to the version they started with.
    """
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not job.pipeline_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job does not have an active pipeline")

    current_pipeline = db.scalar(
        select(Pipeline).where(
            Pipeline.id == job.pipeline_id,
            Pipeline.company_id == current_user.company_id
        )
    )
    if not current_pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    from models.application import Application
    from sqlalchemy import func
    active_apps_count = db.scalar(
        select(func.count(Application.id))
        .join(StageDefinition, Application.current_stage_id == StageDefinition.id)
        .where(
            StageDefinition.pipeline_id == current_pipeline.id,
            Application.company_id == current_user.company_id
        )
    )

    if active_apps_count > 0:
        # Clone current pipeline to new version
        new_version = current_pipeline.pipeline_version + 1
        pipeline = Pipeline(
            company_id=current_user.company_id,
            name=payload.name or current_pipeline.name,
            description=payload.description or current_pipeline.description,
            pipeline_version=new_version,
        )
        db.add(pipeline)
        db.flush()

        for stage_data in payload.stages:
            stage = StageDefinition(
                company_id=current_user.company_id,
                pipeline_id=pipeline.id,
                name=stage_data.name,
                sequence=stage_data.sequence,
                base_category=stage_data.base_category,
                settings=stage_data.settings,
                automation_rules=[rule.model_dump() for rule in stage_data.automation_rules],
                is_active=True,
            )
            db.add(stage)
        
        job.pipeline_id = pipeline.id
        db.commit()
        db.refresh(pipeline)
        
        stages = db.scalars(
            select(StageDefinition).where(
                StageDefinition.pipeline_id == pipeline.id,
                StageDefinition.is_active == True
            ).order_by(StageDefinition.sequence)
        ).all()
        pipeline.stages = stages
        return pipeline
    else:
        # Safely mutate in-place
        if payload.name:
            current_pipeline.name = payload.name
        if payload.description:
            current_pipeline.description = payload.description
        
        # Deactivate or delete old stages
        db.execute(
            delete(StageDefinition).where(StageDefinition.pipeline_id == current_pipeline.id)
        )
        
        for stage_data in payload.stages:
            stage = StageDefinition(
                company_id=current_user.company_id,
                pipeline_id=current_pipeline.id,
                name=stage_data.name,
                sequence=stage_data.sequence,
                base_category=stage_data.base_category,
                settings=stage_data.settings,
                automation_rules=[rule.model_dump() for rule in stage_data.automation_rules],
                is_active=True,
            )
            db.add(stage)
        
        db.commit()
        db.refresh(current_pipeline)
        
        stages = db.scalars(
            select(StageDefinition).where(
                StageDefinition.pipeline_id == current_pipeline.id,
                StageDefinition.is_active == True
            ).order_by(StageDefinition.sequence)
        ).all()
        current_pipeline.stages = stages
        return current_pipeline


# --- Phase B.3A Job-specific Pipeline API Endpoints ---
from core.workflows import ensure_job_stages
from schemas.pipeline import StageDefinitionJobCreate, StageDefinitionJobUpdate, StageDefinitionResponse
from models.pipeline import StageDefinition
from models.job import Job
from models.application import Application
from sqlalchemy import func

@router.get("/{job_id}", response_model=list[StageDefinitionResponse])
def get_job_pipeline_stages(
    job_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Fetches the active stage definitions for a job.
    Automatically initializes the default 8 stages if none exist.
    """
    # Verify job access
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    stages = ensure_job_stages(db, job_id, current_user.company_id)
    # Filter out soft-deleted stages unless explicitly requested (e.g. they are hidden by default)
    active_stages = [s for s in stages if s.deleted_at is None]
    db.commit()
    return active_stages


@router.post("/{job_id}/stages", response_model=StageDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_job_stage(
    job_id: uuid.UUID,
    payload: StageDefinitionJobCreate,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Creates a new custom stage for a job's pipeline.
    """
    # Verify job access
    job = db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.company_id == current_user.company_id
        )
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    with db.begin_nested():
        # Get active stages
        active_stages = list(db.scalars(
            select(StageDefinition)
            .where(
                StageDefinition.job_id == job_id,
                StageDefinition.company_id == current_user.company_id,
                StageDefinition.deleted_at.is_(None)
            )
        ).all())

        # Enforce max 15 stages
        if len(active_stages) >= 15:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 15 stages allowed per job.")

        # Enforce unique name per job (ignoring soft-deleted stages)
        name_lower = payload.name.strip().lower()
        if any(s.name.strip().lower() == name_lower for s in active_stages):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stage name '{payload.name}' already exists for this job.")

        # Calculate position if not provided
        position = payload.position
        if position is None:
            max_pos = max((s.position or 0) for s in active_stages) if active_stages else 0
            position = max_pos + 10

        # Enforce exactly one default stage logic
        if payload.is_default:
            for s in active_stages:
                s.is_default = False
                db.add(s)

        # Enforce terminal validation: terminal stages cannot have outgoing transitions
        if payload.is_terminal and payload.allowed_next_stage_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Terminal stages cannot have outgoing transitions.")

        stage = StageDefinition(
            company_id=current_user.company_id,
            job_id=job_id,
            name=payload.name.strip(),
            base_category=payload.base_category,
            color=payload.color,
            icon=payload.icon,
            position=position,
            sequence=position,
            sla_hours=payload.sla_hours,
            sla_enabled=payload.sla_enabled,
            is_default=payload.is_default,
            is_terminal=payload.is_terminal,
            allowed_next_stage_ids=[str(x) for x in payload.allowed_next_stage_ids] if payload.allowed_next_stage_ids else [],
            is_active=True
        )
        db.add(stage)
        db.flush()

        all_stages = active_stages + [stage]
        has_default = any(s.is_default for s in all_stages)
        has_terminal = any(s.is_terminal for s in all_stages)

        if not has_default:
            all_stages[0].is_default = True
            db.add(all_stages[0])

        if not has_terminal:
            stage.is_terminal = True
            db.add(stage)

    db.commit()
    db.refresh(stage)

    # Log audit event
    log_audit_event(
        db=db,
        action="pipeline.stage_created",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="stage_definition",
        resource_id=str(stage.id),
        metadata={"name": stage.name, "job_id": str(job_id)}
    )

    return stage


@router.patch("/stages/{id}", response_model=StageDefinitionResponse)
def update_job_stage(
    id: uuid.UUID,
    payload: StageDefinitionJobUpdate,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Updates a job-specific hiring stage definition.
    If position is updated, normalize positions using gaps inside a transaction.
    """
    stage = db.scalar(
        select(StageDefinition).where(
            StageDefinition.id == id,
            StageDefinition.company_id == current_user.company_id,
            StageDefinition.deleted_at.is_(None)
        )
    )
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage definition not found")

    with db.begin_nested():
        active_stages = list(db.scalars(
            select(StageDefinition)
            .where(
                StageDefinition.job_id == stage.job_id,
                StageDefinition.company_id == current_user.company_id,
                StageDefinition.deleted_at.is_(None)
            )
        ).all())

        if payload.name is not None:
            name_lower = payload.name.strip().lower()
            if any(s.name.strip().lower() == name_lower and s.id != id for s in active_stages):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stage name '{payload.name}' already exists for this job.")
            stage.name = payload.name.strip()

        if payload.base_category is not None:
            stage.base_category = payload.base_category
        if payload.color is not None:
            stage.color = payload.color
        if payload.icon is not None:
            stage.icon = payload.icon
        if payload.sla_hours is not None:
            stage.sla_hours = payload.sla_hours
        if payload.sla_enabled is not None:
            stage.sla_enabled = payload.sla_enabled
        if payload.is_terminal is not None:
            stage.is_terminal = payload.is_terminal
        if payload.allowed_next_stage_ids is not None:
            stage.allowed_next_stage_ids = [str(x) for x in payload.allowed_next_stage_ids]

        if stage.is_terminal and stage.allowed_next_stage_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Terminal stages cannot have outgoing transitions.")

        if payload.is_default is not None:
            stage.is_default = payload.is_default
            if payload.is_default:
                for s in active_stages:
                    if s.id != id:
                        s.is_default = False
                        db.add(s)

        if payload.position is not None:
            stage.position = payload.position
            stage.sequence = payload.position
            sorted_stages = sorted(active_stages, key=lambda s: (s.position if s.position is not None else 0, s.name))
            for index, s in enumerate(sorted_stages):
                new_pos = (index + 1) * 10
                s.position = new_pos
                s.sequence = new_pos
                db.add(s)

        has_default = any(s.is_default for s in active_stages)
        has_terminal = any(s.is_terminal for s in active_stages)
        if not has_default:
            stage.is_default = True
        if not has_terminal:
            stage.is_terminal = True

        db.add(stage)
        db.flush()

    db.commit()
    db.refresh(stage)

    # Log audit event
    log_audit_event(
        db=db,
        action="pipeline.stage_updated",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="stage_definition",
        resource_id=str(stage.id),
        metadata={"name": stage.name, "job_id": str(stage.job_id)}
    )

    return stage


@router.delete("/stages/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_stage(
    id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Soft-deletes a job stage definition.
    Blocks deletion if there are active candidates in this stage or if minimum stage count (2) is violated.
    """
    stage = db.scalar(
        select(StageDefinition).where(
            StageDefinition.id == id,
            StageDefinition.company_id == current_user.company_id,
            StageDefinition.deleted_at.is_(None)
        )
    )
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage definition not found")

    with db.begin_nested():
        active_stages = list(db.scalars(
            select(StageDefinition)
            .where(
                StageDefinition.job_id == stage.job_id,
                StageDefinition.company_id == current_user.company_id,
                StageDefinition.deleted_at.is_(None)
            )
        ).all())

        if len(active_stages) <= 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hiring pipeline must have at least 2 active stages.")

        active_apps_count = db.scalar(
            select(func.count(Application.id)).where(
                Application.current_stage_id == id,
                Application.company_id == current_user.company_id
            )
        )
        if active_apps_count > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete stage because it contains active applications.")

        stage.deleted_at = func.now()
        db.add(stage)
        db.flush()

        remaining_stages = [s for s in active_stages if s.id != id]
        has_default = any(s.is_default for s in remaining_stages)
        has_terminal = any(s.is_terminal for s in remaining_stages)

        if not has_default and remaining_stages:
            remaining_stages[0].is_default = True
            db.add(remaining_stages[0])

        if not has_terminal and remaining_stages:
            remaining_stages[-1].is_terminal = True
            db.add(remaining_stages[-1])

    db.commit()

    # Log audit event
    log_audit_event(
        db=db,
        action="pipeline.stage_deleted",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="stage_definition",
        resource_id=str(id),
        metadata={"name": stage.name, "job_id": str(stage.job_id)}
    )

