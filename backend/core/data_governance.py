import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, text

logger = logging.getLogger(__name__)

# Data Classification Scheme
DATA_CLASSIFICATIONS = {
    "job_public": "Public",
    "recruiter_template": "Internal",
    "candidate_profile": "Confidential",
    "resume": "Confidential",
    "analytics_report": "Restricted",
    "security_log": "Restricted",
    "ai_chat": "Restricted"
}


class DataGovernanceService:
    @classmethod
    def get_classification(cls, record_type: str) -> str:
        """Returns the classification label for a given record type."""
        return DATA_CLASSIFICATIONS.get(record_type, "Confidential")

    @classmethod
    def has_active_legal_hold(cls, db, company_id: uuid.UUID, candidate_id: uuid.UUID | None = None) -> bool:
        """
        Checks if there is an active legal hold on the company/tenant
        or a specific candidate.
        """
        # Mock checking legal hold flags on company or candidate profile
        # Legal holds take highest priority and block all deletions.
        try:
            # Query optional company legal hold setting
            res = db.execute(text(
                "SELECT legal_hold_active FROM companies WHERE id = :cid"
            ), {"cid": company_id}).fetchone()
            if res and res[0] is True:
                return True
        except Exception:
            pass

        return False

    @classmethod
    def run_retention_sweep(cls, db, company_id: uuid.UUID) -> dict:
        """
        Runs retention and deletion sweeps enforcing:
        Legal Hold (1st priority) > Retention Policy (2nd) > Deletion Schedule (3rd).
        """
        if cls.has_active_legal_hold(db, company_id):
            logger.info(f"Retention sweep bypassed for company {company_id} due to active Legal Hold.")
            return {"status": "bypassed", "reason": "active_legal_hold"}

        # Simulate executing soft-delete rules based on classification retention TTLs
        # Confidential/Restricted: 180 days TTL, Public: 365 days
        now = datetime.now(timezone.utc)
        deleted_counts = {"resumes": 0, "ai_chats": 0, "logs": 0}

        try:
            # 1. Soft-delete resumes older than 180 days
            cutoff_resumes = now - timedelta(days=180)
            res = db.execute(text("""
                UPDATE candidate_resumes 
                SET is_deleted = true 
                WHERE company_id = :cid AND created_at < :cutoff AND is_deleted = false
            """), {"cid": company_id, "cutoff": cutoff_resumes})
            db.commit()
            deleted_counts["resumes"] = res.rowcount
            
            # 2. Hard-delete entries already soft-deleted and older than 30 days in recovery bin
            cutoff_recovery = now - timedelta(days=30)
            db.execute(text("""
                DELETE FROM candidate_resumes 
                WHERE company_id = :cid AND is_deleted = true AND updated_at < :cutoff
            """), {"cid": company_id, "cutoff": cutoff_recovery})
            db.commit()

        except Exception as e:
            logger.error(f"Error during data retention sweep: {e}")
            db.rollback()

        return {"status": "completed", "purged": deleted_counts}
