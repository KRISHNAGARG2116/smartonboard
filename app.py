import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv(override=True)

key = os.getenv("GROQ_API_KEY")
if not key:
    # fallback — hardcode temporarily for testing
    os.environ["GROQ_API_KEY"] = "os.getenv("GROQ_API_KEY")"
    st.error("GROQ_API_KEY not found.")
    st.stop()

from main import onboard_employee
from agents.qa_agent import qa_agent

st.set_page_config(page_title="SmartOnboard", page_icon="🚀", layout="wide")
st.title("🚀 SmartOnboard")
st.subheader("AI-Powered Employee Onboarding System")

with st.sidebar:
    st.header("👤 New Employee Details")
    name = st.text_input("Full Name", placeholder="Krishna Garg")
    role = st.text_input("Role", placeholder="Software Engineer")
    department = st.selectbox("Department", ["Engineering","Marketing","Sales","HR","Finance","Operations","Design"])
    start_date = st.date_input("Start Date")
    email = st.text_input("Email", placeholder="employee@company.com")
    start_btn = st.button("🚀 Start Onboarding", type="primary", use_container_width=True)

if start_btn:
    if not all([name, role, email]):
        st.error("Please fill in all fields!")
    else:
        progress = st.progress(0)
        status = st.empty()
        status.info("🎯 Orchestrator: Planning onboarding...")
        progress.progress(10)

        with st.spinner("Running AI agents..."):
            result = onboard_employee(
                name=name,
                role=role,
                department=department,
                start_date=str(start_date),
                email=email
            )

        progress.progress(100)
        status.success("✅ Onboarding Complete!")
        st.balloons()

        tab1, tab2, tab3, tab4 = st.tabs(["📄 Documents","📚 Training Plan","✉️ Welcome Email","💬 Ask HR Bot"])

        with tab1:
            st.subheader("Generated Documents")
            for i, doc in enumerate(result['documents_generated']):
                with st.expander(f"Document {i+1}", expanded=True):
                    st.markdown(doc)

        with tab2:
            st.subheader("30-60-90 Day Training Plan")
            st.markdown(result['training_plan'])

        with tab3:
            st.subheader("Welcome Email")
            st.markdown(result['email_draft'])

        with tab4:
            st.subheader("Ask anything about the onboarding")
            if "messages" not in st.session_state:
                st.session_state.messages = []
            if "onboard_result" not in st.session_state:
                st.session_state.onboard_result = result
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            if question := st.chat_input("Ask about policies, schedule, team..."):
                st.session_state.messages.append({"role": "user", "content": question})
                with st.chat_message("user"):
                    st.markdown(question)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        answer = qa_agent(result, question)
                    st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

else:
    st.info("👈 Fill in the employee details on the left and click **Start Onboarding**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Agents", "4", "Active")
    with col2:
        st.metric("Documents", "2", "Generated")
    with col3:
        st.metric("Training Plan", "90 days", "Personalised")
    with col4:
        st.metric("Time Saved", "~3 hours", "Per hire")