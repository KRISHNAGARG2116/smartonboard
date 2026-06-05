import re

COMMON_SKILLS_VOCABULARY = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "ruby", "php", "swift", "kotlin", "rust",
    "react", "angular", "vue", "next.js", "node.js", "django", "flask", "spring", "asp.net", "laravel",
    "sql", "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "nosql",
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "github", "ci/cd", "jenkins", "terraform", "ansible",
    "html", "css", "tailwind", "sass", "graphql", "rest api", "grpc", "microservices",
    "machine learning", "deep learning", "ai", "nlp", "computer vision", "tensorflow", "pytorch",
    "agile", "scrum", "project management", "product management", "system design", "data structures", "algorithms",
    "communication", "teamwork", "leadership", "problem solving"
}


def calculate_candidate_job_match(
    candidate_skills: list[str] | None,
    job_title: str,
    job_description: str,
    job_settings: dict | None = None
) -> dict:
    """Calculates the applicability score, matching skills, and missing skills.
    
    If the job settings has a configured 'required_skills' list, it is used.
    Otherwise, the title and description are scanned against a vocabulary of standard skills.
    """
    candidate_skills = candidate_skills or []
    cand_skills_lower = {skill.lower() for skill in candidate_skills}
    
    # 1. Determine job required skills
    required_skills = []
    if job_settings and isinstance(job_settings.get("required_skills"), list):
        required_skills = [str(s) for s in job_settings["required_skills"]]
    else:
        # Fallback: scan description & title against common vocabulary
        full_text = f"{job_title} {job_description}".lower()
        # Find matches from vocabulary using word boundary searches
        matched_vocab = []
        for skill in COMMON_SKILLS_VOCABULARY:
            # Escape skill for safe regex boundary matching
            escaped = re.escape(skill)
            if re.search(rf"\b{escaped}\b", full_text):
                matched_vocab.append(skill)
        required_skills = matched_vocab

    if not required_skills:
        # Handle jobs with no configured/detected required skills gracefully
        return {
            "applicability_score": 100,
            "matching_skills": [],
            "missing_skills": []
        }

    # 2. Compare skills (case-insensitive matching)
    matching_skills = []
    missing_skills = []
    
    # Track lower-cased items to prevent duplicates
    matched_lower = set()
    
    for req in required_skills:
        req_lower = req.lower()
        # Direct check in candidate's skills
        if req_lower in cand_skills_lower:
            matching_skills.append(req)
            matched_lower.add(req_lower)
        else:
            missing_skills.append(req)

    # 3. Calculate score
    total = len(required_skills)
    score = int((len(matching_skills) / total) * 100) if total > 0 else 100
    
    return {
        "applicability_score": score,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills
    }
