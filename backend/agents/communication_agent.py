import os

def communication_agent(candidate_data: dict, decision_result: dict, job_description: str) -> dict:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    name = candidate_data.get('name', 'Candidate')
    decision = decision_result.get('decision', 'REJECT')

    print(f"\n Communication Agent: Drafting {decision} email for {name}")

    if decision == "HIRE":
        prompt = f"""Write a warm, professional offer email to {name} for the position they applied for.
        Include: congratulations, next steps, excitement about them joining, a request to confirm their start date.
        Sign off as 'The HR Team'"""

    elif decision == "INTERVIEW":
        questions = decision_result.get('suggested_interview_questions', [])
        prompt = f"""Write a professional interview invitation email to {name}.
        Include: they've been shortlisted, interview scheduling placeholder, what to prepare.
        Topics they may be asked about: {questions}
        Sign off as 'The HR Team'"""

    else:
        prompt = f"""Write a kind, professional rejection email to {name}.
        Include: thank them for applying, encourage them to apply for future roles.
        Do NOT mention specific reasons for rejection.
        Sign off as 'The HR Team'"""

    result = llm.invoke(prompt)
    print(f" Communication Agent: {decision} email drafted")

    return {
        "email_type": decision,
        "email_content": result.content,
        "recipient": candidate_data.get('email', 'unknown')
    }
