from langgraph.graph import StateGraph, END
from state import OnboardingState
from agents.orchestrator import orchestrator_agent
from agents.document_agent import document_agent
from agents.training_agent import training_agent
from agents.email_agent import email_agent

def create_onboarding_graph():
    graph = StateGraph(OnboardingState)
    
    # Add all agents as nodes
    graph.add_node("orchestrator", orchestrator_agent)
    graph.add_node("document_agent", document_agent)
    graph.add_node("training_agent", training_agent)
    graph.add_node("email_agent", email_agent)
    
    # Connect them in order
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
        "current_step": "orchestrator",
        "errors": []
    }
    
    print("\n" + "="*50)
    print("🚀 SMARTONBOARD — Starting Onboarding Pipeline")
    print("="*50)
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("✅ ONBOARDING COMPLETE")
    print("="*50)
    print(f"\n📋 Documents generated: {len(result['documents_generated'])}")
    print(f"📚 Training plan: {'✅' if result['training_plan'] else '❌'}")
    print(f"✉️  Welcome email: {'✅' if result['email_sent'] else '❌'}")
    
    return result

if __name__ == "__main__":
    result = onboard_employee(
        name="Krishna Garg",
        role="Software Engineer",
        department="Engineering",
        start_date="June 15, 2026",
        email="krishnagarg2116@gmail.com"
    )
    
    print("\n\n=== GENERATED DOCUMENTS ===")
    for doc in result['documents_generated']:
        print(doc[:300] + "...\n")
    
    print("\n=== TRAINING PLAN (first 300 chars) ===")
    print(result['training_plan'][:300] + "...")
    
    print("\n=== WELCOME EMAIL ===")
    print(result['email_draft'][:300] + "...")