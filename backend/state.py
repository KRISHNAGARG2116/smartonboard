from typing import TypedDict, List, Dict, Any, Optional

class OnboardingState(TypedDict):
    employee_name: str
    role: str
    department: str
    start_date: str
    email: str
    documents_generated: List[str]
    training_plan: str
    qa_context: str
    email_draft: str
    email_sent: bool
    resume_path: str
    resume_bytes: bytes
    job_description: str
    candidate_data: Dict[str, Any]
    screening_result: Dict[str, Any]
    scoring_result: Dict[str, Any]
    decision_result: Dict[str, Any]
    communication_result: Dict[str, Any]
    current_step: str
    errors: List[str]
