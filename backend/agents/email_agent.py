import os

def email_agent(state):
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n Email Agent: Drafting welcome email for {state['employee_name']}")

    email_draft = llm.invoke(
        f"""Write a warm, professional welcome email to a new employee:
        Name: {state['employee_name']}
        Role: {state['role']}
        Department: {state['department']}
        Start Date: {state['start_date']}

        Include:
        - Warm welcome from the team
        - What to expect on day 1
        - Who to contact for help
        - 3 things to do before their first day
        - Excited, friendly tone

        Format it as a proper email with Subject line."""
    )

    print(f" Email Agent: Welcome email drafted")

    return {
        **state,
        "email_draft": email_draft.content,
        "email_sent": True,
        "current_step": "complete"
    }
