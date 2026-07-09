from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import Application, StageDefinition, Candidate
from models.job import Job
import uuid

router = APIRouter(prefix="/candidate/applications", tags=["candidate-timeline"])

@router.get("/{id}/timeline")
def get_timeline(
    id: uuid.UUID,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # Fetch application
    app = None
    if candidate_ids:
        app = db.scalar(
            select(Application).where(
                Application.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Fetch job
    job = db.scalar(select(Job).where(Job.id == app.job_id))
    if not job or not job.pipeline_id:
        raise HTTPException(status_code=400, detail="Job or job pipeline definition not found")

    # Fetch all stages for the pipeline
    stages = db.scalars(
        select(StageDefinition)
        .where(StageDefinition.pipeline_id == job.pipeline_id)
        .order_by(StageDefinition.sequence.asc())
    ).all()

    # De-duplicate stages by ID to ensure no duplicated definitions
    seen_ids = set()
    unique_stages = []
    for stage in stages:
        if stage.id not in seen_ids:
            seen_ids.add(stage.id)
            unique_stages.append(stage)

    # Filter out hidden stages (handle bool and string 'true' case-insensitively)
    visible_stages = []
    for stage in unique_stages:
        val = stage.settings.get("hide_from_candidate") if stage.settings else None
        hidden = False
        if val is not None:
            if isinstance(val, bool):
                hidden = val
            elif isinstance(val, str):
                hidden = val.lower() == "true"
        if not hidden:
            visible_stages.append(stage)

    # Map output stages
    timeline_stages = []
    current_stage_idx = -1
    for idx, stage in enumerate(visible_stages):
        timeline_stages.append({
            "id": str(stage.id),
            "name": stage.name,
            "base_category": stage.base_category,
            "sequence": stage.sequence
        })
        if stage.id == app.current_stage_id:
            current_stage_idx = idx

    # If current stage is hidden, walk backward to find the latest visible stage
    if current_stage_idx == -1 and app.current_stage_id is not None:
        all_stage_ids = [s.id for s in unique_stages]
        if app.current_stage_id in all_stage_ids:
            orig_idx = all_stage_ids.index(app.current_stage_id)
            # Find closest previous visible stage
            for prev_idx in range(orig_idx - 1, -1, -1):
                prev_stage_id = all_stage_ids[prev_idx]
                for v_idx, v_stage in enumerate(visible_stages):
                    if v_stage.id == prev_stage_id:
                        current_stage_idx = v_idx
                        break
                if current_stage_idx != -1:
                    break

    return {
        "stages": timeline_stages,
        "current_stage_index": current_stage_idx,
        "application_status": app.status
    }

