import os

def orchestrator_agent(state):
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n Orchestrator: Starting onboarding for {state['employee_name']} - {state['role']}")

    summary = llm.invoke(
        f"""You are an HR orchestrator. A new employee is joining:
        Name: {state['employee_name']}
        Role: {state['role']}
        Department: {state['department']}
        Start Date: {state['start_date']}

        Write a brief 3-sentence onboarding plan summary for this person.
        Be specific to their role and department."""
    )

    print(f" Orchestrator: Plan created")

    return {
        **state,
        "current_step": "document_agent",
        "qa_context": summary.content
    }
