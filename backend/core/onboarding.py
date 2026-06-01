from sqlalchemy.orm import Session
from models import Employee, OnboardingTemplate, OnboardingWorkflow, OnboardingTask, OnboardingDocument
from datetime import datetime, date

class OnboardingEngine:
    @staticmethod
    def _rules_match(employee: Employee, rule_criteria: dict) -> bool:
        """
        Evaluates dynamic rules against employee fields.
        If a rule criteria dictionary is empty, it matches all employees.
        e.g., {"department": "Engineering"} matches if employee.department == "Engineering".
        """
        if not rule_criteria:
            return True
        for key, value in rule_criteria.items():
            emp_val = getattr(employee, key, None)
            if isinstance(emp_val, str) and isinstance(value, str):
                if emp_val.lower() != value.lower():
                    return False
            elif emp_val != value:
                return False
        return True

    @staticmethod
    def _determine_assignee(task_type: str) -> str:
        """Maps task type to a default assignee role."""
        if task_type in ("document_signature", "form_filling"):
            return "candidate"
        elif task_type == "it_provisioning":
            return "it_admin"
        else:
            return "recruiter"

    @classmethod
    def evaluate_and_assign(
        cls, 
        db: Session, 
        employee: Employee, 
        template: OnboardingTemplate
    ) -> OnboardingWorkflow:
        """Evaluates dynamic rules against employee properties to construct the checklist."""
        workflow = OnboardingWorkflow(
            company_id=employee.company_id,
            employee_id=employee.id,
            status="initiated",
            started_at=datetime.utcnow()
        )
        db.add(workflow)
        db.flush()  # Generate workflow.id

        for t_task in template.tasks:
            if cls._rules_match(employee, t_task.rule_criteria):
                task = OnboardingTask(
                    company_id=employee.company_id,
                    workflow_id=workflow.id,
                    title=t_task.title,
                    description=t_task.description,
                    status="pending",
                    task_type=t_task.task_type,
                    sequence=t_task.sequence,
                    assigned_to_role=cls._determine_assignee(t_task.task_type),
                    due_date=employee.start_date,
                    meta_payload={}
                )
                db.add(task)
                db.flush()  # Generate task.id

                # If this task requires signature, create the onboarding document record
                if t_task.task_type == "document_signature":
                    doc_name = t_task.title.replace("Sign ", "").replace("Upload ", "").replace("Submit ", "")
                    doc = OnboardingDocument(
                        company_id=employee.company_id,
                        task_id=task.id,
                        document_name=doc_name,
                        signature_status="pending_candidate"
                    )
                    db.add(doc)

        return workflow
