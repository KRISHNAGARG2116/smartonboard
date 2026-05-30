import os
import json
import re

def screening_agent(candidate_data: dict, job_description: str) -> dict:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print(f"\n Screening Agent: Checking {candidate_data.get('name', 'candidate')} against JD")

    result = llm.invoke(
        f"""You are an expert HR screener. Compare this candidate against the job description.

        CANDIDATE:
        Name: {candidate_data.get('name')}
        Skills: {candidate_data.get('skills')}
        Experience: {candidate_data.get('experience_years')} years
        Education: {candidate_data.get('education')}
        Previous Roles: {candidate_data.get('previous_roles')}
        Summary: {candidate_data.get('summary')}

        JOB DESCRIPTION:
        {job_description}

        Return ONLY a JSON object:
        {{
            "matches": ["requirement that candidate meets"],
            "gaps": ["requirement that candidate is missing"],
            "experience_match": true or false,
            "education_match": true or false,
            "skills_match_percentage": 0-100,
            "screening_notes": "2-3 sentence assessment"
        }}

        Return ONLY the JSON, no other text."""
    )

    content = result.content.strip()
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            print(f" Screening Agent: {parsed.get('skills_match_percentage', 0)}% skills match")
            return parsed
        except json.JSONDecodeError:
            pass

    return {
        "matches": [],
        "gaps": [],
        "experience_match": False,
        "education_match": False,
        "skills_match_percentage": 0,
        "screening_notes": "Could not parse screening results"
    }


def screen_resume_text(resume_text: str, job_role: str, job_description: str = "") -> dict:
    """Lightweight screening from raw resume text (used by /api/screen endpoint)."""
    from langchain_groq import ChatGroq
    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    analysis = llm.invoke(
        f"""You are an expert HR recruiter. Analyze this resume for the role of {job_role}.

        Job Role: {job_role}
        Job Description: {job_description if job_description else "Not provided"}

        Resume:
        {resume_text}

        Return ONLY valid JSON with these exact keys:
        {{
          "score": 0-100,
          "strengths": ["strength1", "strength2"],
          "concerns": ["concern1"],
          "skills": ["skill1", "skill2"],
          "experience_years": "X",
          "education": "degree and institution",
          "recommendation": "STRONG_YES or YES or MAYBE or NO",
          "summary": "2-3 sentence summary"
        }}"""
    )

    content = analysis.content.strip()
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {
        "score": 70,
        "strengths": ["Relevant background"],
        "concerns": ["Some gaps"],
        "skills": ["Communication"],
        "experience_years": "Unknown",
        "education": "Not specified",
        "recommendation": "MAYBE",
        "summary": content[:300]
    }
