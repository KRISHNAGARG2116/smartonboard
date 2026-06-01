import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import (
    Employee,
    OnboardingDocument,
    OnboardingTask,
    OnboardingDocumentSignature,
    OnboardingActivityLog
)
from core.audit import log_audit_event


def log_onboarding_activity(
    db: Session,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    actor_type: str,
    event_type: str,
    metadata: dict
) -> OnboardingActivityLog:
    """
    Creates an immutable onboarding activity timeline entry.
    Every timeline record is completely read-only and represents a chronological transition.
    """
    activity = OnboardingActivityLog(
        company_id=company_id,
        employee_id=employee_id,
        actor_id=actor_id,
        actor_type=actor_type,
        event_type=event_type,
        metadata_json=metadata,
        created_at=datetime.now(timezone.utc)
    )
    db.add(activity)
    db.flush()
    return activity


class OnboardingSignatureService:
    @staticmethod
    def generate_signature_hash(
        employee_id: uuid.UUID,
        document_id: uuid.UUID,
        signer_name: str,
        signed_at: datetime
    ) -> str:
        """
        Generates a secure cryptographically strong SHA-256 signature fingerprint.
        """
        raw_payload = f"{employee_id}:{document_id}:{signer_name}:{signed_at.isoformat()}:smartonboard-compliance-salt-2026"
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    @classmethod
    def sign_document(
        cls,
        db: Session,
        employee_id: uuid.UUID,
        document_id: uuid.UUID,
        signer_name: str,
        signature_text: str,
        ip_address: str,
        user_agent: str,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "candidate"
    ) -> OnboardingDocumentSignature:
        """
        Executes a legally-binding compliance document signing action.
        Updates the onboarding document state, completes the parent task if all docs are signed,
        and logs the auditable activity and compliance events.
        """
        # 1. Resolve Onboarding Document and verify existence
        doc = db.scalar(select(OnboardingDocument).where(OnboardingDocument.id == document_id))
        if not doc:
            raise ValueError("Onboarding document not found")
            
        task = db.scalar(select(OnboardingTask).where(OnboardingTask.id == doc.task_id))
        if not task:
            raise ValueError("Parent onboarding task not found")

        # Verify employee access
        emp = db.scalar(select(Employee).where(Employee.id == employee_id))
        if not emp:
            raise ValueError("Employee profile not found")

        # 2. Cryptographic signature generation
        signed_at = datetime.now(timezone.utc)
        sig_hash = cls.generate_signature_hash(
            employee_id=employee_id,
            document_id=document_id,
            signer_name=signer_name,
            signed_at=signed_at
        )

        # 3. Create the Signature record
        signature = OnboardingDocumentSignature(
            company_id=emp.company_id,
            employee_id=employee_id,
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
            signer_name=signer_name,
            signature_hash=sig_hash,
            signed_at=signed_at
        )
        db.add(signature)

        # 4. Update OnboardingDocument completion parameters
        doc.signature_status = "signed"
        doc.signed_at = signed_at
        db.add(doc)
        db.flush()

        # 5. Onboarding Activity Timeline Logging
        log_onboarding_activity(
            db=db,
            company_id=emp.company_id,
            employee_id=employee_id,
            actor_id=actor_id or employee_id,
            actor_type=actor_type,
            event_type="document_signed",
            metadata={
                "document_id": str(document_id),
                "document_name": doc.document_name,
                "signer_name": signer_name,
                "signature_text": signature_text,
                "signature_hash": sig_hash
            }
        )

        # 6. Check if all documents associated with the parent task are completed
        sibling_docs = db.scalars(select(OnboardingDocument).where(OnboardingDocument.task_id == task.id)).all()
        all_completed = all(d.signature_status == "signed" for d in sibling_docs)

        if all_completed and task.status != "completed":
            task.status = "completed"
            task.completed_at = signed_at
            task.completed_by_id = actor_id or employee_id
            db.add(task)
            
            # Log task completion in Onboarding Activity Log
            log_onboarding_activity(
                db=db,
                company_id=emp.company_id,
                employee_id=employee_id,
                actor_id=actor_id or employee_id,
                actor_type=actor_type,
                event_type="task_completed",
                metadata={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "task_type": task.task_type
                }
            )

            # Check if all tasks in the workflow are now completed, transitioning workflow status
            workflow_tasks = db.scalars(select(OnboardingTask).where(OnboardingTask.workflow_id == task.workflow_id)).all()
            all_wf_completed = all(t.status == "completed" for t in workflow_tasks)
            if all_wf_completed:
                from models import OnboardingWorkflow
                wf = db.scalar(select(OnboardingWorkflow).where(OnboardingWorkflow.id == task.workflow_id))
                if wf and wf.status != "completed":
                    wf.status = "completed"
                    wf.completed_at = signed_at
                    db.add(wf)

                    # Log onboarding completion event
                    log_onboarding_activity(
                        db=db,
                        company_id=emp.company_id,
                        employee_id=employee_id,
                        actor_id=None,
                        actor_type="system",
                        event_type="onboarding_completed",
                        metadata={
                            "workflow_id": str(wf.id)
                        }
                    )

        # 7. Generate compliance audit log event
        log_audit_event(
            db=db,
            action="onboarding.document_signed",
            actor_type=actor_type,
            company_id=emp.company_id,
            actor_id=actor_id or employee_id,
            resource_type="onboarding_document",
            resource_id=str(document_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "signer_name": signer_name,
                "signature_hash": sig_hash
            }
        )

        return signature
