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


    try:
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
    except Exception as llm_exc:
        print(f"Groq LLM call failed in resume parser: {llm_exc}. Using regex/heuristic fallback parser.")

    # Heuristic fallback parsing
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
    email = email_match.group(0) if email_match else "unknown@example.com"

    # Simple phone match
    phone_match = re.search(r'\+?\d[\d\-\(\)\s]{8,15}', resume_text)
    phone = phone_match.group(0).strip() if phone_match else "Unknown"

    # Simple name extraction (first line or words before email)
    name = "Unknown Candidate"
    lines = [l.strip() for l in resume_text.split('\n') if l.strip()]
    if lines:
        for line in lines[:3]:
            if len(line.split()) <= 4 and not any(x in line.lower() for x in ['resume', 'cv', 'curriculum', 'profile', 'page']):
                name = line
                break

    # Simple skills extraction
    common_skills = ['python', 'javascript', 'typescript', 'react', 'node', 'fastapi', 'sql', 'postgres', 'docker', 'aws', 'git', 'html', 'css', 'java', 'c++', 'go', 'rust']
    skills = []
    for skill in common_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', resume_text.lower()):
            skills.append(skill.capitalize() if skill != 'sql' else 'SQL')

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "experience_years": 1,
        "education": "Unknown",
        "previous_roles": [],
        "summary": lines[0] if lines else "No summary available."
    }
