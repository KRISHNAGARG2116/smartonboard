from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv(override=True)

if not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "os.getenv("GROQ_API_KEY")"

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

def qa_agent(state, question):
    answer = llm.invoke(
        f"""You are a helpful HR assistant for a new employee.
        
        Employee: {state['employee_name']}
        Role: {state['role']}
        Department: {state['department']}
        
        Context about their onboarding:
        {state['qa_context']}
        
        Answer this question helpfully and concisely:
        {question}"""
    )
    return answer.content