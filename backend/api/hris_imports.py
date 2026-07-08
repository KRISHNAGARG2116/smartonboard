import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb, RequireOwner
from models.hris_import import GreenhouseLeverImport
from models.candidate import Candidate
from models.application import Application
from models.job import Job
from models.enums import ApplicationStatus
from core.celery_app import celery_app
from db.session import tenant_context, SessionLocal
from models.integration_audit_log import IntegrationAuditLog
from integrations.base.factory import ProviderFactory

router = APIRouter(prefix="/hris/import", tags=["hris_imports"])


class ImportTriggerPayload(BaseModel):
    provider: str  # 'greenhouse', 'lever'


class ImportProgressResponse(BaseModel):
    id: uuid.UUID
    provider: str
    progress_pct: int
    imported_count: int
    skipped_count: int
    failed_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=ImportProgressResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_hris_import(
    payload: ImportTriggerPayload,
    current_user: RequireRecruiter,
    db: TenantDb
):
    if payload.provider not in ("greenhouse", "lever"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider. Must be greenhouse or lever.")

    # Create progress record
    import_job = GreenhouseLeverImport(
        company_id=current_user.company_id,
        provider=payload.provider,
        progress_pct=0,
        imported_count=0,
        skipped_count=0,
        failed_count=0,
        status="pending"
    )
    db.add(import_job)
    db.commit()
    db.refresh(import_job)

    # Spawn Celery async task
    run_hris_import_task.delay(str(current_user.company_id), str(import_job.id))
    return import_job


@router.get("/jobs", response_model=List[ImportProgressResponse])
def list_import_jobs(
    current_user: RequireRecruiter,
    db: TenantDb
):
    stmt = select(GreenhouseLeverImport).where(
        GreenhouseLeverImport.company_id == current_user.company_id
    ).order_by(GreenhouseLeverImport.created_at.desc())
    jobs = db.scalars(stmt).all()
    return list(jobs)


@router.get("/jobs/{job_id}/errors")
def download_import_errors_csv(
    job_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    # Returns a mock error CSV file of failed import records
    import_job = db.scalar(
        select(GreenhouseLeverImport).where(
            GreenhouseLeverImport.id == job_id,
            GreenhouseLeverImport.company_id == current_user.company_id
        )
    )
    if not import_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "Email", "Reason"])
    writer.writerow([4, "failed.email@example.com", "Invalid resume structure or parsing exception"])
    writer.writerow([12, "incomplete.email@example.com", "Missing candidate full name"])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=import_errors_{job_id}.csv"}
    )


@celery_app.task
def run_hris_import_task(company_id_str: str, import_job_id_str: str):
    """Asynchronous worker processing Greenhouse/Lever candidates import."""
    company_id = uuid.UUID(company_id_str)
    job_id = uuid.UUID(import_job_id_str)

    with tenant_context(tenant_id=str(company_id)):
        db = SessionLocal()
        import_job = db.get(GreenhouseLeverImport, job_id)
        if not import_job:
            db.close()
            return

        import_job.status = "processing"
        import_job.progress_pct = 10
        db.add(import_job)
        db.commit()

        try:
            # Instantiate adapter
            provider = ProviderFactory.get_provider("hris", import_job.provider)
            credentials = {"api_key": "mock"}
            candidates = provider.import_candidates(credentials)

            total = len(candidates)
            imported = 0
            skipped = 0
            failed = 0

            # Select default active job in company for import target
            first_job = db.scalar(select(Job).where(Job.company_id == company_id))

            for idx, raw_candidate in enumerate(candidates):
                # Update progress
                import_job.progress_pct = int(10 + (80 * ((idx + 1) / total)))
                db.add(import_job)
                db.commit()

                email = raw_candidate.get("email")
                full_name = f"{raw_candidate.get('first_name', '')} {raw_candidate.get('last_name', '')}".strip() or raw_candidate.get("full_name")

                if not email or not full_name:
                    failed += 1
                    continue

                # Check if candidate already exists
                existing = db.scalar(select(Candidate).where(Candidate.email == email))
                if existing:
                    skipped += 1
                    continue

                # Create Candidate
                candidate = Candidate(
                    company_id=company_id,
                    email=email,
                    full_name=full_name,
                )
                db.add(candidate)
                db.flush()

                # Create Application
                if first_job:
                    application = Application(
                        company_id=company_id,
                        candidate_id=candidate.id,
                        job_id=first_job.id,
                        status=ApplicationStatus.APPLIED,
                        source=raw_candidate.get("source", "HRIS Import")
                    )
                    db.add(application)
                    db.flush()

                imported += 1

            # Complete job
            import_job.imported_count = imported
            import_job.skipped_count = skipped
            import_job.failed_count = failed
            import_job.status = "completed"
            import_job.progress_pct = 100
            db.add(import_job)

            # Audit log
            audit = IntegrationAuditLog(
                company_id=company_id,
                integration_type="hris",
                action="hris.imported",
                status="success",
                details_json={"provider": import_job.provider, "imported": imported, "skipped": skipped, "failed": failed}
            )
            db.add(audit)
            db.commit()

        except Exception as e:
            import_job.status = "failed"
            import_job.progress_pct = 100
            db.add(import_job)
            
            audit = IntegrationAuditLog(
                company_id=company_id,
                integration_type="hris",
                action="hris.import_failed",
                status="failure",
                details_json={"provider": import_job.provider, "error": str(e)}
            )
            db.add(audit)
            db.commit()
        finally:
            db.close()
