from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import CandidateMessage, Application, Candidate
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/candidate/messages", tags=["candidate-messages"])

class SendMessageSchema(BaseModel):
    application_id: uuid.UUID
    content: str
    thread_id: uuid.UUID | None = None
    parent_message_id: uuid.UUID | None = None
    attachments_json: list | None = None

class EditMessageSchema(BaseModel):
    content: str
    client_updated_at: datetime

class ReactMessageSchema(BaseModel):
    reaction: str

@router.get("")
def list_messages(
    current_candidate: RequireCandidate,
    db: CandidateDb,
    application_id: uuid.UUID | None = None
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # Retrieve messages for applications belonging to this candidate
    stmt = select(CandidateMessage).join(
        Application, CandidateMessage.application_id == Application.id
    ).where(Application.candidate_id.in_(candidate_ids))

    if application_id:
        stmt = stmt.where(Application.id == application_id)

    stmt = stmt.order_by(CandidateMessage.created_at.asc())
    messages = []
    if candidate_ids:
        messages = db.scalars(stmt).all()

    return [
        {
            "id": str(msg.id),
            "application_id": str(msg.application_id),
            "sender_id": str(msg.sender_id),
            "sender_role": msg.sender_role,
            "content": msg.content if not msg.deleted_at else "This message was deleted",
            "attachments_json": msg.attachments_json if not msg.deleted_at else [],
            "status": msg.status,
            "thread_id": str(msg.thread_id) if msg.thread_id else None,
            "parent_message_id": str(msg.parent_message_id) if msg.parent_message_id else None,
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
            "reactions_json": msg.reactions_json,
            "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
            "created_at": msg.created_at.isoformat(),
            "updated_at": msg.updated_at.isoformat()
        }
        for msg in messages
    ]

@router.post("")
def send_message(
    body: SendMessageSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    # Fetch recruiter Candidate record IDs matching this user's email
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # Verify candidate owns the application
    app = None
    if candidate_ids:
        app = db.scalar(
            select(Application).where(
                Application.id == body.application_id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not app:
        raise HTTPException(status_code=403, detail="Access denied: Application not owned by candidate")

    msg = CandidateMessage(
        company_id=app.company_id,
        application_id=body.application_id,
        sender_id=current_candidate.id,
        sender_role="candidate",
        content=body.content,
        attachments_json=body.attachments_json or [],
        status="sent",
        thread_id=body.thread_id or uuid.uuid4(),
        parent_message_id=body.parent_message_id
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {
        "id": str(msg.id),
        "status": msg.status,
        "thread_id": str(msg.thread_id),
        "created_at": msg.created_at.isoformat()
    }

@router.post("/{id}/read")
def mark_read(
    id: uuid.UUID,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    msg = None
    if candidate_ids:
        msg = db.scalar(
            select(CandidateMessage).join(
                Application, CandidateMessage.application_id == Application.id
            ).where(
                CandidateMessage.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.sender_role != "candidate" and msg.status != "read":
        msg.status = "read"
        msg.read_at = datetime.now(timezone.utc)
        db.add(msg)
        db.commit()

    return {"status": "success"}

@router.post("/{id}/react")
def react_message(
    id: uuid.UUID,
    body: ReactMessageSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    msg = None
    if candidate_ids:
        msg = db.scalar(
            select(CandidateMessage).join(
                Application, CandidateMessage.application_id == Application.id
            ).where(
                CandidateMessage.id == id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    reactions = dict(msg.reactions_json or {})
    user_str = str(current_candidate.id)
    reactions[user_str] = body.reaction
    msg.reactions_json = reactions
    db.add(msg)
    db.commit()
    return {"status": "success", "reactions": msg.reactions_json}

@router.put("/{id}")
def edit_message(
    id: uuid.UUID,
    body: EditMessageSchema,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    msg = None
    if candidate_ids:
        msg = db.scalar(
            select(CandidateMessage).join(
                Application, CandidateMessage.application_id == Application.id
            ).where(
                CandidateMessage.id == id,
                Application.candidate_id.in_(candidate_ids),
                CandidateMessage.sender_id == current_candidate.id
            )
        )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found or you are not the sender")

    # Optimistic Concurrency check
    if body.client_updated_at is not None:
        db_updated = msg.updated_at
        client_updated = body.client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Message has been modified by another process. Please reload and try again."
                )

    msg.content = body.content
    msg.edited_at = datetime.now(timezone.utc)
    db.add(msg)
    db.commit()
    return {"status": "success"}

@router.delete("/{id}")
def delete_message(
    id: uuid.UUID,
    client_updated_at: datetime,
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    msg = None
    if candidate_ids:
        msg = db.scalar(
            select(CandidateMessage).join(
                Application, CandidateMessage.application_id == Application.id
            ).where(
                CandidateMessage.id == id,
                Application.candidate_id.in_(candidate_ids),
                CandidateMessage.sender_id == current_candidate.id
            )
        )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found or you are not the sender")

    # Optimistic Concurrency check
    if client_updated_at is not None:
        db_updated = msg.updated_at
        client_updated = client_updated_at
        if db_updated and client_updated:
            db_u_naive = db_updated.astimezone(timezone.utc).replace(tzinfo=None) if db_updated.tzinfo else db_updated
            cl_u_naive = client_updated.astimezone(timezone.utc).replace(tzinfo=None) if client_updated.tzinfo else client_updated
            if db_u_naive > cl_u_naive + timedelta(milliseconds=1):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Message has been modified by another process. Please reload and try again."
                )

    msg.deleted_at = datetime.now(timezone.utc)
    db.add(msg)
    db.commit()
    return {"status": "success"}
