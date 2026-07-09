from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import CandidateTask
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/candidate/tasks", tags=["candidate-tasks"])

class CompleteTaskSchema(BaseModel):
    meta_payload: dict
    client_updated_at: datetime

@router.get("")
def list_tasks(
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    tasks = db.scalars(
        select(CandidateTask).where(CandidateTask.candidate_id == current_candidate.id)
    ).all()
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "task_type": t.task_type,
            "meta_payload": t.meta_payload,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "updated_at": t.updated_at.isoformat()
        }
        for t in tasks
    ]

@router.post("/{id}/complete")
def complete_task(
    id: uuid.UUID,
    body: CompleteTaskSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    task = db.scalar(
        select(CandidateTask).where(
            CandidateTask.id == id,
            CandidateTask.candidate_id == current_candidate.id
        )
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated = task.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Task has been modified by another process. Please reload and try again."
                )

    task.status = "completed"
    task.meta_payload = body.meta_payload
    task.completed_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
    return {"status": "success"}
