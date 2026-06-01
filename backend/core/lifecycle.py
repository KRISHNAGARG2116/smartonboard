import uuid
from datetime import date, datetime
from sqlalchemy.orm import Session
from models import (
    Application,
    Employee,
    OnboardingTemplate,
    OnboardingTemplateTask,
    OnboardingWorkflow,
    OnboardingEventOutbox
)
from models.enums import ApplicationStatus
from core.onboarding import OnboardingEngine
from core.audit import log_audit_event

class CandidateToEmployeeService:
    @staticmethod
    def convert_candidate_to_employee(
        db: Session,
        application_id: uuid.UUID,
        employment_type: str,
        employee_number: str | None = None,
        supervisor_id: uuid.UUID | None = None,
        current_user_id: uuid.UUID | None = None,
        request_ip: str | None = None,
        request_ua: str | None = None,
        company_id: uuid.UUID | None = None
    ) -> Employee:
        """
        Atomically converts a candidate application into an employee profile.
        Sets application status to hired, creates the Employee record, instantiates
        the onboarding checklist using rules engine, and logs audit and outbox events.
        """
        # 1. Fetch Application & Candidate
        query = db.query(Application).filter(Application.id == application_id)
        if company_id:
            query = query.filter(Application.company_id == company_id)
        application = query.first()
        if not application:
            raise ValueError("Application not found")
        
        candidate = application.candidate
        if not candidate:
            raise ValueError("Candidate not found for application")

        # 2. Check if employee already exists with this email under this tenant
        existing_emp = db.query(Employee).filter(
            Employee.company_id == application.company_id,
            Employee.email == candidate.email
        ).first()
        if existing_emp:
            raise ValueError("Employee profile already exists with this email")

        # 3. Resolve Job and Offer details
        job_title = "New Hire"
        start_date = date.today()

        if application.job:
            job_title = application.job.title

        offer = application.offer
        if offer:
            start_date = offer.start_date
            # Offer may override job title, otherwise keep job title
            if hasattr(offer, "job_title") and getattr(offer, "job_title"):
                job_title = offer.job_title

        # 4. Create the Employee profile record
        employee = Employee(
            company_id=application.company_id,
            candidate_id=candidate.id,
            email=candidate.email,
            full_name=candidate.full_name,
            phone=candidate.phone,
            job_title=job_title,
            department=application.job.department if application.job else None,
            employment_type=employment_type,
            employee_number=employee_number,
            status="onboarding",
            start_date=start_date,
            supervisor_id=supervisor_id
        )
        db.add(employee)
        db.flush()  # Generate employee.id

        # 5. Set Application status to hired
        application.status = ApplicationStatus.HIRED

        # 6. Fetch or Bootstraps a default onboarding template
        template = db.query(OnboardingTemplate).filter(
            OnboardingTemplate.company_id == application.company_id,
            OnboardingTemplate.is_default == True
        ).first()

        if not template:
            # Check for any template
            template = db.query(OnboardingTemplate).filter(
                OnboardingTemplate.company_id == application.company_id
            ).first()

        if not template:
            # Bootstrap a lightweight default template
            template = OnboardingTemplate(
                company_id=application.company_id,
                name="Default Onboarding Template",
                description="Automatically generated default onboarding sequence",
                is_default=True
            )
            db.add(template)
            db.flush()

            default_tasks = [
                ("Sign Employee NDA", "Please review and sign the company non-disclosure agreement.", "document_signature", 1),
                ("Fill Payroll Form", "Please submit your direct deposit details.", "form_filling", 2),
                ("Configure Workstation Setup", "Request workstation, access keys, and corporate accounts.", "it_provisioning", 3),
            ]
            for title, desc, t_type, seq in default_tasks:
                t_task = OnboardingTemplateTask(
                    company_id=application.company_id,
                    template_id=template.id,
                    title=title,
                    description=desc,
                    sequence=seq,
                    task_type=t_type,
                    rule_criteria={}
                )
                db.add(t_task)
            db.flush()

        # 7. Evaluate and assign onboarding checklist
        workflow = OnboardingEngine.evaluate_and_assign(db, employee, template)

        # Log Onboarding Activity Log events
        from core.signatures import log_onboarding_activity
        log_onboarding_activity(
            db=db,
            company_id=employee.company_id,
            employee_id=employee.id,
            actor_id=current_user_id,
            actor_type="recruiter" if current_user_id else "system",
            event_type="onboarding_started",
            metadata={"workflow_id": str(workflow.id)}
        )

        for task in workflow.tasks:
            log_onboarding_activity(
                db=db,
                company_id=employee.company_id,
                employee_id=employee.id,
                actor_id=current_user_id,
                actor_type="recruiter" if current_user_id else "system",
                event_type="task_created",
                metadata={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "task_type": task.task_type
                }
            )

        # 8. Write 'employee.created' event to Transactional Outbox
        outbox = OnboardingEventOutbox(
            company_id=employee.company_id,
            event_type="employee.created",
            payload={
                "employee_id": str(employee.id),
                "email": employee.email,
                "full_name": employee.full_name,
                "job_title": employee.job_title,
                "employment_type": employee.employment_type,
                "start_date": str(employee.start_date),
                "workflow_id": str(workflow.id)
            },
            status="pending"
        )
        db.add(outbox)

        # 9. Log compliance audit event
        if current_user_id:
            log_audit_event(
                db=db,
                action="employee.transitioned",
                actor_type="RECRUITER",
                actor_id=current_user_id,
                company_id=employee.company_id,
                resource_type="employees",
                resource_id=str(employee.id),
                ip_address=request_ip,
                user_agent=request_ua,
                metadata={
                    "employee_id": str(employee.id),
                    "candidate_id": str(candidate.id),
                    "application_id": str(application_id),
                    "job_title": employee.job_title,
                    "workflow_id": str(workflow.id)
                }
            )

        db.commit()
        return employee
