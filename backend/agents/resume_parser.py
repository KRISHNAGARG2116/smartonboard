import os
import io
import json
import re

def resume_parser_agent(pdf_bytes: bytes) -> dict:
    from langchain_groq import ChatGroq
    from pypdf import PdfReader

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print("\n Resume Parser: Extracting text from PDF")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    result = llm.invoke(
        f"""Extract information from this resume and return ONLY a JSON object with these exact keys:
        {{
            "name": "full name",
            "email": "email address",
            "phone": "phone number",
            "skills": ["skill1", "skill2"],
            "experience_years": 0,
            "education": "highest degree and institution",
            "previous_roles": ["role1", "role2"],
            "summary": "2 sentence professional summary"
        }}

        Resume text:
        {resume_text}

        Return ONLY the JSON, no other text."""
    )

    content = result.content.strip()
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            print(f" Resume Parser: Extracted data for {parsed.get('name', 'Unknown')}")
            return parsed
        except json.JSONDecodeError:
            pass

    return {
        "name": "Unknown",
        "email": "unknown@example.com",
        "phone": "Unknown",
        "skills": [],
        "experience_years": 0,
        "education": "Unknown",
        "previous_roles": [],
        "summary": resume_text[:200]
    }
