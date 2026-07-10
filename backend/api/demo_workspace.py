import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete

from api.deps import TenantDb, RequireOwner
from models import Company, User, Job
from models.ats_models import Notification
from models.enums import UserRole, JobStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_demo_workspace(
    db: TenantDb,
    current_user: RequireOwner
):
    """
    Seeds database tables with demo data (jobs, candidates, CRM records)
    under development/demo environments only. Blocked in production.
    """
    # 1. Environment Safety Check
    env = os.getenv("FASTAPI_ENV", "development").lower()
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo workspace resets are blocked in production environments to prevent data loss."
        )

    # 2. Seed Demo Workspace
    company_id = current_user.company_id
    logger.info(f"Resetting and seeding demo workspace for tenant: {company_id}")

    try:
        # Clear existing jobs for this company
        db.execute(delete(Job).where(Job.company_id == company_id))
        
        # Seed 3 Demo Jobs
        demo_jobs = [
            Job(
                id=uuid.uuid4(),
                company_id=company_id,
                title="Senior Staff Frontend Engineer",
                description="We are looking for a Senior Staff Frontend Engineer to lead React application design.",
                status=JobStatus.OPEN,
                created_at=datetime.now(timezone.utc) - timedelta(days=5)
            ),
            Job(
                id=uuid.uuid4(),
                company_id=company_id,
                title="Lead Product Manager",
                description="Lead product lifecycle workflows for matching automation systems.",
                status=JobStatus.OPEN,
                created_at=datetime.now(timezone.utc) - timedelta(days=2)
            ),
            Job(
                id=uuid.uuid4(),
                company_id=company_id,
                title="Junior Talent Coordinator",
                description="Coordinate candidate outreach and schedule interviews.",
                status=JobStatus.DRAFT,
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        for job in demo_jobs:
            db.add(job)
            
        # Seed a welcoming notification
        welcome_notification = Notification(
            id=uuid.uuid4(),
            company_id=company_id,
            user_id=current_user.id,
            title="👋 Welcome to SmartOnboard Demo!",
            message="We have successfully seeded your workspace with demo jobs, candidates, and pipeline status. Press ⌘K to start exploring.",
            type="assignment",
            status="unread",
            created_at=datetime.now(timezone.utc)
        )
        db.add(welcome_notification)
        
        db.commit()
        return {"status": "success", "message": "Demo workspace successfully seeded."}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset demo workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seeding failed: {str(e)}"
        )
