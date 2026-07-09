from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from api.deps import RequireCandidate, CandidateDb
from models import CandidateDocument, Application
import uuid
import hashlib
import os

router = APIRouter(prefix="/candidate/documents", tags=["candidate-documents"])

@router.get("")
def list_documents(
    current_candidate: RequireCandidate,
    db: CandidateDb
):
    docs = db.scalars(
        select(CandidateDocument)
        .where(CandidateDocument.candidate_id == current_candidate.id)
        .order_by(CandidateDocument.document_type.asc(), CandidateDocument.version.desc())
    ).all()

    return [
        {
            "id": str(d.id),
            "application_id": str(d.application_id),
            "document_type": d.document_type,
            "document_name": d.document_name,
            "storage_path": d.storage_path,
            "version": d.version,
            "status": d.status,
            "uploaded_by_id": str(d.uploaded_by_id),
            "reviewed_by_id": str(d.reviewed_by_id) if d.reviewed_by_id else None,
            "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
            "review_reason": d.review_reason,
            "verification_status_reason_code": d.verification_status_reason_code,
            "verified_checksum": d.verified_checksum,
            "verification_reason_code": d.verification_status_reason_code,
            "checksum": d.verified_checksum,
            "mime_type": d.mime_type,
            "file_size": d.file_size,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat()
        }
        for d in docs
    ]


@router.post("/upload")
async def upload_document(
    current_candidate: RequireCandidate,
    db: CandidateDb,
    application_id: uuid.UUID = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    # Fetch recruiter Candidate record IDs matching this user's email
    from models import Candidate
    candidate_ids = db.scalars(
        select(Candidate.id).where(Candidate.email == current_candidate.email)
    ).all()

    # Verify candidate owns the application
    app = None
    if candidate_ids:
        app = db.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.candidate_id.in_(candidate_ids)
            )
        )
    if not app:
        raise HTTPException(status_code=403, detail="Access denied: Application not owned by candidate")

    # Read file content and calculate metadata
    content = await file.read()
    file_size = len(content)
    mime_type = file.content_type or "application/octet-stream"
    checksum = hashlib.sha256(content).hexdigest()

    # Determine version number
    highest_version = db.scalar(
        select(func.max(CandidateDocument.version))
        .where(
            CandidateDocument.candidate_id == current_candidate.id,
            CandidateDocument.application_id == application_id,
            CandidateDocument.document_type == document_type
        )
    ) or 0
    new_version = highest_version + 1

    # Ensure storage folder exists
    storage_dir = f"storage/documents/{str(current_candidate.id)}"
    os.makedirs(storage_dir, exist_ok=True)
    filename = f"{document_type}_v{new_version}_{file.filename}"
    file_path = os.path.join(storage_dir, filename)

    # Write file to storage
    with open(file_path, "wb") as f:
        f.write(content)

    # Create immutable CandidateDocument entry
    doc = CandidateDocument(
        company_id=app.company_id,
        application_id=application_id,
        candidate_id=current_candidate.id,
        document_type=document_type,
        document_name=file.filename,
        storage_path=file_path,
        version=new_version,
        status="pending",
        uploaded_by_id=current_candidate.id,
        verified_checksum=checksum,
        mime_type=mime_type,
        file_size=file_size
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "id": str(doc.id),
        "version": doc.version,
        "status": doc.status,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "verified_checksum": doc.verified_checksum,
        "checksum": doc.verified_checksum,
        "verification_reason_code": doc.verification_status_reason_code
    }

