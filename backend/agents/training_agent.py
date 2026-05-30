import os

def training_agent(state):
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n Training Agent: Building learning plan for {state['role']}")

    training_plan = llm.invoke(
        f"""Create a detailed 30-60-90 day onboarding training plan for:
        Role: {state['role']}
        Department: {state['department']}

        For each phase include:
        - Key goals
        - Specific skills to learn
        - Tools to master
        - People to meet
        - Success metrics

        Be specific, actionable, and realistic."""
    )

    print(f" Training Agent: Learning plan created")

    return {
        **state,
        "training_plan": training_plan.content,
        "current_step": "email_agent"
    }
