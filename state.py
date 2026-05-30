from typing import TypedDict, List, Optional, Dict, Any

class OnboardingState(TypedDict):
    # Employee info
    employee_name: str
    role: str
    department: str
    start_date: str
    email: str

    # Agent outputs — onboarding
    documents_generated: List[str]
    training_plan: str
    qa_context: str
    email_draft: str
    email_sent: bool

    # Recruitment fields
    resume_path: str
    resume_bytes: bytes
    job_description: str
    candidate_data: Dict[str, Any]
    screening_result: Dict[str, Any]
    scoring_result: Dict[str, Any]
    decision_result: Dict[str, Any]
    communication_result: Dict[str, Any]

    # Tracking
    current_step: str
    errors: List[str]