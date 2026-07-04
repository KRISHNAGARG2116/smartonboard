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
    job_settings: dict | None = None,
    candidate_summary: str | None = None,
    candidate_location: str | None = None
) -> dict:
    """Calculates the applicability score using a weighted multi-factor fit check.
    
    Factors checked:
    - Required Skills (configurable weight)
    - Preferred Skills (10% default weight)
    - Experience Years (configurable weight)
    - Education Level (configurable weight)
    - Certifications & Languages (configurable weights)
    - Location Compatibility (Remote/Hybrid check, relocation willingness)
    - Work Authorization Compatibility
    """
    candidate_skills = candidate_skills or []
    cand_skills_lower = {skill.lower() for skill in candidate_skills}
    job_settings = job_settings or {}

    # 1. Required Skills Match
    required_skills = []
    if isinstance(job_settings.get("required_skills"), list):
        required_skills = [str(s) for s in job_settings["required_skills"]]
    else:
        # Fallback: scan description & title against common vocabulary
        full_text = f"{job_title} {job_description}".lower()
        matched_vocab = []
        for skill in COMMON_SKILLS_VOCABULARY:
            escaped = re.escape(skill)
            if re.search(rf"\b{escaped}\b", full_text):
                matched_vocab.append(skill)
        required_skills = matched_vocab

    matching_skills = []
    missing_skills = []
    for req in required_skills:
        req_lower = req.lower()
        if req_lower in cand_skills_lower:
            matching_skills.append(req)
        else:
            missing_skills.append(req)

    skills_score = len(matching_skills) / len(required_skills) if required_skills else 1.0

    # 2. Preferred Skills Match
    preferred_skills = job_settings.get("preferred_skills") or []
    matching_preferred = []
    for pref in preferred_skills:
        if pref.lower() in cand_skills_lower:
            matching_preferred.append(pref)
    preferred_score = len(matching_preferred) / len(preferred_skills) if preferred_skills else 1.0

    # 3. Experience Match
    min_exp = job_settings.get("min_experience_years")
    experience_years = 0
    if candidate_summary:
        exp_matches = re.findall(r"(\d+)\+?\s*years?", candidate_summary.lower())
        if exp_matches:
            experience_years = max(int(m) for m in exp_matches)
    if min_exp is not None and min_exp > 0:
        exp_score = min(1.0, experience_years / min_exp)
    else:
        exp_score = 1.0

    # 4. Education Match
    EDUCATION_LEVELS = {"high school": 1, "associate": 2, "bachelor": 3, "master": 4, "phd": 5}
    req_edu = job_settings.get("education")
    cand_edu_level = 1
    if candidate_summary:
        summary_lower = candidate_summary.lower()
        if "phd" in summary_lower or "ph.d" in summary_lower or "doctorate" in summary_lower:
            cand_edu_level = 5
        elif "master" in summary_lower or "m.s." in summary_lower or "mba" in summary_lower:
            cand_edu_level = 4
        elif "bachelor" in summary_lower or "b.s." in summary_lower or "degree" in summary_lower:
            cand_edu_level = 3
        elif "associate" in summary_lower:
            cand_edu_level = 2
    if req_edu:
        req_edu_level = EDUCATION_LEVELS.get(req_edu.lower(), 1)
        edu_score = min(1.0, cand_edu_level / req_edu_level)
    else:
        edu_score = 1.0

    # 5. Certifications Match
    req_certs = job_settings.get("certifications") or []
    matching_certs = []
    if req_certs and candidate_summary:
        summary_lower = candidate_summary.lower()
        for cert in req_certs:
            if cert.lower() in summary_lower:
                matching_certs.append(cert)
    certs_score = len(matching_certs) / len(req_certs) if req_certs else 1.0

    # 6. Languages Match
    req_langs = job_settings.get("languages") or []
    matching_langs = []
    if req_langs and candidate_summary:
        summary_lower = candidate_summary.lower()
        for lang in req_langs:
            if lang.lower() in summary_lower:
                matching_langs.append(lang)
    langs_score = len(matching_langs) / len(req_langs) if req_langs else 1.0

    # 7. Location Compatibility
    workplace_type = job_settings.get("workplace_type", "On-site")
    reloc_offered = job_settings.get("relocation_offered", False)
    
    loc_score = 1.0
    if workplace_type != "Remote" and candidate_location:
        willing_relocate = False
        if candidate_summary:
            willing_relocate = "reloc" in candidate_summary.lower() or "willing to relocate" in candidate_summary.lower()
        
        job_loc = job_settings.get("location") or ""
        if job_loc.lower() in candidate_location.lower() or candidate_location.lower() in job_loc.lower():
            loc_score = 1.0
        elif reloc_offered and willing_relocate:
            loc_score = 1.0
        else:
            loc_score = 0.5
            
    # 8. Work Authorization Compatibility
    visa_spons = job_settings.get("visa_sponsorship", False)
    auth_score = 1.0
    if not visa_spons and candidate_summary:
        summary_lower = candidate_summary.lower()
        if "sponsorship" in summary_lower or "visa" in summary_lower or "need sponsorship" in summary_lower:
            auth_score = 0.2

    # 9. Weighted Fit Calculation
    w_skills = job_settings.get("skills_weight", 0.40)
    w_pref = 0.10
    w_exp = job_settings.get("experience_weight", 0.20)
    w_edu = job_settings.get("education_weight", 0.10)
    w_cert = job_settings.get("certification_weight", 0.05)
    w_lang = job_settings.get("language_weight", 0.05)
    w_loc = job_settings.get("location_weight", 0.05)
    w_auth = job_settings.get("work_authorization_weight", 0.05)

    # Normalize weights to sum to 1.0
    total_weight = w_skills + w_pref + w_exp + w_edu + w_cert + w_lang + w_loc + w_auth
    if total_weight > 0:
        w_skills /= total_weight
        w_pref /= total_weight
        w_exp /= total_weight
        w_edu /= total_weight
        w_cert /= total_weight
        w_lang /= total_weight
        w_loc /= total_weight
        w_auth /= total_weight

    score = (
        skills_score * w_skills +
        preferred_score * w_pref +
        exp_score * w_exp +
        edu_score * w_edu +
        certs_score * w_cert +
        langs_score * w_lang +
        loc_score * w_loc +
        auth_score * w_auth
    ) * 100

    return {
        "applicability_score": int(score),
        "matching_skills": matching_skills,
        "missing_skills": missing_skills
    }

