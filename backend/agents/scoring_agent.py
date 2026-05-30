import os
import json
import re
from dotenv import load_dotenv

load_dotenv()


def scoring_agent(
    candidate_data: dict, screening_result: dict, job_description: str
) -> dict:
    from langchain_groq import ChatGroq

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n📊 Scoring Agent: Scoring {candidate_data.get('name', 'Unknown')}")

    result = llm.invoke(
        f"""You are a senior HR expert. Evaluate this candidate for the job and give an honest score.

        CANDIDATE:
        {candidate_data}

        SCREENING RESULT:
        {screening_result}

        JOB DESCRIPTION:
        {job_description}

        Use your expertise to score this candidate fairly. Consider their overall ability to do this job well.

        Return ONLY a JSON object:
        {{
            "total_score": 0-100,
            "skills_score": 0-100,
            "experience_score": 0-100,
            "education_score": 0-100,
            "overall_fit": "Excellent/Good/Average/Poor",
            "strengths": ["strength1", "strength2"],
            "weaknesses": ["weakness1", "weakness2"],
            "scoring_reasoning": "3-4 sentence detailed reasoning"
        }}

        Return ONLY the JSON, no other text."""
    )

    content = result.content.strip()
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            print(
                f"✅ Scoring Agent: {parsed.get('total_score', 0)}/100 — {parsed.get('overall_fit', 'Unknown')}"
            )
            return parsed
        except json.JSONDecodeError:
            pass

    return {
        "total_score": 0,
        "skills_score": 0,
        "experience_score": 0,
        "education_score": 0,
        "overall_fit": "Poor",
        "strengths": [],
        "weaknesses": [],
        "scoring_reasoning": "Could not parse scoring results",
    }
