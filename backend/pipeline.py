from langgraph.graph import StateGraph, END
from state import OnboardingState
from agents.orchestrator import orchestrator_agent
from agents.document_agent import document_agent
from agents.training_agent import training_agent
from agents.email_agent import email_agent
from agents.resume_parser import resume_parser_agent
from agents.screening_agent import screening_agent
from agents.scoring_agent import scoring_agent
from agents.decision_agent import decision_agent
from agents.communication_agent import communication_agent


def create_onboarding_graph():
    graph = StateGraph(OnboardingState)
    graph.add_node("orchestrator", orchestrator_agent)
    graph.add_node("document_agent", document_agent)
    graph.add_node("training_agent", training_agent)
    graph.add_node("email_agent", email_agent)
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "document_agent")
    graph.add_edge("document_agent", "training_agent")
    graph.add_edge("training_agent", "email_agent")
    graph.add_edge("email_agent", END)
    return graph.compile()


def onboard_employee(name, role, department, start_date, email):
    app = create_onboarding_graph()
    initial_state = {
        "employee_name": name,
        "role": role,
        "department": department,
        "start_date": start_date,
        "email": email,
        "documents_generated": [],
        "training_plan": "",
        "qa_context": "",
        "email_draft": "",
        "email_sent": False,
        "resume_path": "",
        "resume_bytes": b"",
        "job_description": "",
        "candidate_data": {},
        "screening_result": {},
        "scoring_result": {},
        "decision_result": {},
        "communication_result": {},
        "current_step": "orchestrator",
        "errors": []
    }
    return app.invoke(initial_state)


def create_recruitment_graph():
    graph = StateGraph(OnboardingState)

    def run_resume_parser(state):
        result = resume_parser_agent(state["resume_bytes"])
        return {
            **state,
            "candidate_data": result,
            "employee_name": result.get("name", ""),
            "email": result.get("email", ""),
        }

    def run_screening(state):
        result = screening_agent(state["candidate_data"], state["job_description"])
        return {**state, "screening_result": result}

    def run_scoring(state):
        result = scoring_agent(state["candidate_data"], state["screening_result"], state["job_description"])
        return {**state, "scoring_result": result}

    def run_decision(state):
        result = decision_agent(state["candidate_data"], state["scoring_result"], state["job_description"])
        return {**state, "decision_result": result}

    def run_communication(state):
        result = communication_agent(state["candidate_data"], state["decision_result"], state["job_description"])
        return {**state, "communication_result": result}

    def run_orchestrator(state):
        if state["decision_result"].get("decision") == "HIRE":
            return orchestrator_agent(state)
        return {**state, "current_step": "complete"}

    def run_document(state):
        if state["decision_result"].get("decision") == "HIRE":
            return document_agent(state)
        return state

    def run_training(state):
        if state["decision_result"].get("decision") == "HIRE":
            return training_agent(state)
        return state

    def run_email(state):
        if state["decision_result"].get("decision") == "HIRE":
            return email_agent(state)
        return state

    graph.add_node("resume_parser", run_resume_parser)
    graph.add_node("screening", run_screening)
    graph.add_node("scoring", run_scoring)
    graph.add_node("decision", run_decision)
    graph.add_node("communication", run_communication)
    graph.add_node("orchestrator", run_orchestrator)
    graph.add_node("document_agent", run_document)
    graph.add_node("training_agent", run_training)
    graph.add_node("email_agent", run_email)

    graph.set_entry_point("resume_parser")
    graph.add_edge("resume_parser", "screening")
    graph.add_edge("screening", "scoring")
    graph.add_edge("scoring", "decision")
    graph.add_edge("decision", "communication")
    graph.add_edge("communication", "orchestrator")
    graph.add_edge("orchestrator", "document_agent")
    graph.add_edge("document_agent", "training_agent")
    graph.add_edge("training_agent", "email_agent")
    graph.add_edge("email_agent", END)

    return graph.compile()


def process_candidate(pdf_bytes: bytes, job_description: str, role: str, department: str, start_date: str):
    app = create_recruitment_graph()
    initial_state = {
        "employee_name": "",
        "role": role,
        "department": department,
        "start_date": start_date,
        "email": "",
        "documents_generated": [],
        "training_plan": "",
        "qa_context": "",
        "email_draft": "",
        "email_sent": False,
        "resume_path": "",
        "resume_bytes": pdf_bytes,
        "job_description": job_description,
        "candidate_data": {},
        "screening_result": {},
        "scoring_result": {},
        "decision_result": {},
        "communication_result": {},
        "current_step": "resume_parser",
        "errors": []
    }
    return app.invoke(initial_state)
