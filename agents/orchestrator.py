from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("os.getenv("GROQ_API_KEY")"),
    model_name="llama-3.3-70b-versatile"
)

def orchestrator_agent(state):
    print(f"\n🎯 Orchestrator: Starting onboarding for {state['employee_name']} - {state['role']}")
    
    summary = llm.invoke(
        f"""You are an HR orchestrator. A new employee is joining:
        Name: {state['employee_name']}
        Role: {state['role']}
        Department: {state['department']}
        Start Date: {state['start_date']}
        
        Write a brief 3-sentence onboarding plan summary for this person.
        Be specific to their role and department."""
    )
    
    print(f"✅ Orchestrator: Plan created")
    
    return {
        **state,
        "current_step": "document_agent",
        "qa_context": summary.content
    }