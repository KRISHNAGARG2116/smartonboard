import os
import json
import re

def decision_agent(candidate_data: dict, scoring_result: dict, job_description: str) -> dict:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n Decision Agent: Making decision for {candidate_data.get('name', 'candidate')}")

    result = llm.invoke(
        f"""You are a senior HR decision maker. Make a final hiring decision.

        CANDIDATE: {candidate_data.get('name')}
        Total Score: {scoring_result.get('total_score')}/100
        Overall Fit: {scoring_result.get('overall_fit')}
        Strengths: {scoring_result.get('strengths')}
        Weaknesses: {scoring_result.get('weaknesses')}
        Reasoning: {scoring_result.get('scoring_reasoning')}

        JOB DESCRIPTION: {job_description}

        Rules:
        - Score 80+ = HIRE
        - Score 60-79 = INTERVIEW
        - Score below 60 = REJECT
        - Always flag borderline cases (55-65) for human review

        Return ONLY a JSON object:
        {{
            "decision": "HIRE or INTERVIEW or REJECT",
            "confidence": "High or Medium or Low",
            "decision_reasoning": "3-4 sentence explanation",
            "suggested_interview_questions": ["question1", "question2", "question3"],
            "salary_recommendation": "salary range suggestion",
            "flag_for_human_review": true or false,
            "flag_reason": "reason if flagged, else empty string"
        }}

        Return ONLY the JSON, no other text."""
    )

    content = result.content.strip()
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            print(f" Decision Agent: {parsed.get('decision')} — {parsed.get('confidence')} confidence")
            return parsed
        except json.JSONDecodeError:
            pass

    return {
        "decision": "INTERVIEW",
        "confidence": "Low",
        "decision_reasoning": "Could not parse decision — manual review required",
        "suggested_interview_questions": [],
        "salary_recommendation": "To be determined",
        "flag_for_human_review": True,
        "flag_reason": "Parsing error"
    }
