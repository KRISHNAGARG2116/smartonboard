import os
import io
import json
import re

def resume_parser_agent(pdf_bytes: bytes) -> dict:
    from langchain_groq import ChatGroq
    from pypdf import PdfReader

    llm = ChatGroq(model_name="llama-3.3-70b-versatile")

    print("\n Resume Parser: Extracting text from document bytes")
    import puremagic
    ext = ".txt"
    try:
        matches = puremagic.magic_string(pdf_bytes)
        if matches:
            matches.sort(key=lambda x: x.confidence, reverse=True)
            matched_ext = matches[0].extension.lower()
            if matched_ext == ".zip":
                ext = ".docx"
            elif matched_ext in {".pdf", ".docx"}:
                ext = matched_ext
    except Exception:
        pass
        
    try:
        from core.signature import extract_text_from_file_bytes
        resume_text = extract_text_from_file_bytes(pdf_bytes, f"resume{ext}")
    except Exception as exc:
        print(f"Error extracting text in resume parser: {exc}")
        resume_text = ""


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
