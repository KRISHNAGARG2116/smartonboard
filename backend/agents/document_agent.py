import os

def document_agent(state):
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n Document Agent: Generating documents for {state['employee_name']}")

    offer_letter = llm.invoke(
        f"""Generate a professional offer letter for:
        Name: {state['employee_name']}
        Role: {state['role']}
        Department: {state['department']}
        Start Date: {state['start_date']}

        Include: welcome message, role responsibilities,
        reporting structure, and first day instructions.
        Keep it professional and warm."""
    )

    policy_summary = llm.invoke(
        f"""Generate a company policy summary for a new {state['role']} joining the {state['department']} department.
        Include: work hours, leave policy, code of conduct,
        communication tools, and IT setup instructions.
        Keep it concise and friendly."""
    )

    documents = [
        f"=== OFFER LETTER ===\n{offer_letter.content}",
        f"=== POLICY SUMMARY ===\n{policy_summary.content}"
    ]

    print(f" Document Agent: Generated {len(documents)} documents")

    return {
        **state,
        "documents_generated": documents,
        "current_step": "training_agent"
    }
