import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request

from api.deps import RequireRecruiter, TenantDb
from models import Application, CandidateNote
from schemas.note import NoteCreateRequest, NoteResponse, NoteUpdateRequest
from core.audit import log_audit_event
from sqlalchemy import select

router = APIRouter(prefix="/applications/{application_id}/notes", tags=["notes"])


def _get_application(application_id: uuid.UUID, db: TenantDb, current_user: RequireRecruiter) -> Application:
    # Under tenant context, RLS is active but we still check explicitly
    app_record = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.company_id == current_user.company_id
        )
    )
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app_record


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    application_id: uuid.UUID,
    body: NoteCreateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    note = CandidateNote(
        company_id=current_user.company_id,
        application_id=application_id,
        user_id=current_user.id,
        content=body.content
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    # Log audit event
    log_audit_event(
        db=db,
        action="note.created",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="candidate_notes",
        resource_id=str(note.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "note_id": str(note.id)
        }
    )

    return note


@router.get("", response_model=List[NoteResponse])
def list_notes(
    application_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    # Verify application exists
    _get_application(application_id, db, current_user)

    stmt = select(CandidateNote).where(
        CandidateNote.application_id == application_id,
        CandidateNote.company_id == current_user.company_id
    ).order_by(CandidateNote.created_at.asc())
    
    return list(db.scalars(stmt).all())


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    application_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteUpdateRequest,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    note = db.scalar(
        select(CandidateNote).where(
            CandidateNote.id == note_id,
            CandidateNote.application_id == application_id,
            CandidateNote.company_id == current_user.company_id
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    old_content = note.content
    note.content = body.content
    db.commit()
    db.refresh(note)

    # Log audit event
    log_audit_event(
        db=db,
        action="note.updated",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="candidate_notes",
        resource_id=str(note.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "note_id": str(note.id)
        }
    )

    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    application_id: uuid.UUID,
    note_id: uuid.UUID,
    request: Request,
    current_user: RequireRecruiter,
    db: TenantDb,
):
    app_record = _get_application(application_id, db, current_user)

    note = db.scalar(
        select(CandidateNote).where(
            CandidateNote.id == note_id,
            CandidateNote.application_id == application_id,
            CandidateNote.company_id == current_user.company_id
        )
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    db.delete(note)
    db.commit()

    # Log audit event
    log_audit_event(
        db=db,
        action="note.deleted",
        actor_type="RECRUITER",
        actor_id=current_user.id,
        company_id=current_user.company_id,
        resource_type="candidate_notes",
        resource_id=str(note_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "application_id": str(application_id),
            "candidate_id": str(app_record.candidate_id),
            "actor_id": str(current_user.id),
            "note_id": str(note_id)
        }
    )
