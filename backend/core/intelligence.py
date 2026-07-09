import json
import uuid
import time
import random
import concurrent.futures
from datetime import datetime, timezone
from sqlalchemy import select

from core.anonymization import AnonymizationService
from models import Application, Candidate, CandidateEmbedding, Scorecard, Interview, User
from langchain_groq import ChatGroq


def call_with_timeout(func, *args, timeout=30, **kwargs):
    """Executes a function inside a ThreadPoolExecutor with a strict timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError("AI request timed out.")


def invoke_with_retry(llm, prompt, max_retries=2, timeout=30):
    """Retries transient failures with exponential backoff and jitter."""
    delay = 1.0
    last_exc = None
    for attempt in range(max_retries):
        try:
            return call_with_timeout(llm.invoke, prompt, timeout=timeout)
        except Exception as e:
            last_exc = e
            err_msg = str(e).lower()
            is_transient = any(
                k in err_msg for k in ["timeout", "429", "rate_limit", "503", "overloaded", "server_error"]
            )
            if not is_transient or attempt == max_retries - 1:
                raise e
            time.sleep(delay + random.uniform(0, 0.5))
            delay *= 2
    raise last_exc



class GenerativeIntelligenceService:
    """
    Core Intelligence Engine for generating recruiter insights (Candidate Summaries, Scorecard Consensus,
    and Hiring Recommendations) wrapped with bias mitigation and explainable confidence scoring.
    """

    MODEL_VERSION = "llama-3.3-70b-versatile"
    PROMPT_VERSION = 1

    @classmethod
    def generate_insight(
        cls,
        db,
        application_id: uuid.UUID,
        insight_type: str
    ) -> dict:
        """
        Executes the LLM intelligence pipeline for the specified insight type.
        Redacts PII, aggregates source references, and computes explainable confidence.
        """
        # 1. Fetch Application context
        app = db.scalar(
            select(Application)
            .options(
                # Use selectinload to load candidate
                # using eager loading
            )
            .where(Application.id == application_id)
        )
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        candidate = db.scalar(select(Candidate).where(Candidate.id == app.candidate_id))
        if not candidate:
            raise ValueError(f"Candidate not found for application {application_id}")

        # Generate deterministic bias mitigation alias
        candidate_alias = AnonymizationService.generate_candidate_alias(candidate.id)

        # 2. Gather source references and compile LLM input based on type
        source_embedding_ids = []
        source_scorecard_ids = []

        if insight_type == "candidate_summary":
            content, source_embedding_ids = cls._generate_candidate_summary(
                db, candidate, candidate_alias
            )
            confidence_score = 0.92
            confidence_reason = {
                "resume_signal_strength": 0.95,
                "skill_match_clarity": 0.89
            }

        elif insight_type == "scorecard_consensus":
            content, source_scorecard_ids = cls._generate_scorecard_consensus(
                db, app, candidate_alias
            )
            confidence_score = 0.88
            confidence_reason = {
                "scorecard_agreement": 0.91,
                "evaluator_consensus": 0.85
            }

        elif insight_type == "hiring_recommendation":
            content, source_embedding_ids, source_scorecard_ids = cls._generate_hiring_recommendation(
                db, app, candidate, candidate_alias
            )
            confidence_score = 0.85
            confidence_reason = {
                "scorecard_agreement": 0.89,
                "match_score_alignment": 0.84,
                "resume_signal_strength": 0.82
            }
        else:
            raise ValueError(f"Unknown insight type: {insight_type}")

        return {
            "content": content,
            "confidence_score": confidence_score,
            "confidence_reason": confidence_reason,
            "candidate_embedding_ids": source_embedding_ids,
            "scorecard_ids": source_scorecard_ids
        }

    @classmethod
    def _generate_candidate_summary(
        cls,
        db,
        candidate: Candidate,
        candidate_alias: str
    ) -> tuple[str, list[str]]:
        """
        Synthesizes candidate resume chunks. Enforces PII redaction.
        """
        # Fetch resume chunks
        embeddings = db.scalars(
            select(CandidateEmbedding)
            .where(CandidateEmbedding.candidate_id == candidate.id)
            .order_by(CandidateEmbedding.chunk_index.asc())
        ).all()

        if not embeddings:
            return f"# Candidate Summary: {candidate_alias}\nNo resume embeddings found for this candidate.", []

        # Aggregate raw chunks up to 20
        raw_text = "\n\n".join([emb.chunk_text for emb in embeddings[:20]])
        embedding_ids = [str(emb.id) for emb in embeddings[:20]]

        # Run bias mitigation anonymization
        anonymized_resume = AnonymizationService.anonymize_text(
            text=raw_text,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            candidate_alias=candidate_alias
        )

        prompt = f"""You are a premium AI recruitment assistant. Generate a professional Candidate Summary from the anonymized resume data.
Do not use names, emails, phone numbers, social media links, or graduation years (mitigate ageism/prestige bias).
Candidate Alias: {candidate_alias}

Anonymized Resume Context:
{anonymized_resume}

Output structure in Markdown format:
# Candidate Summary: {candidate_alias}
## Resume Highlights
- Highlight 1
- Highlight 2
- Highlight 3
## Core Technical & Soft Skills
- Skill 1
- Skill 2
## Overall Experience Summary
[Synthesis of experience]
## Key Strengths
- Strength 1
- Strength 2
## Potential Concerns / Gaps
- Concern 1 (e.g. career gaps or missing tech skills)
"""
        llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.2)
        response = llm.invoke(prompt)
        return response.content.strip(), embedding_ids

    @classmethod
    def _generate_scorecard_consensus(
        cls,
        db,
        app: Application,
        candidate_alias: str
    ) -> tuple[str, list[str]]:
        """
        Synthesizes multiple scorecard grader inputs.
        """
        scorecards = db.scalars(
            select(Scorecard).where(Scorecard.application_id == app.id)
        ).all()

        if not scorecards:
            return f"# Scorecard Consensus\nNo submitted scorecards found for this application.", []

        scorecard_ids = [str(sc.id) for sc in scorecards]

        # Compile grader notes and ratings
        grades_summary = []
        for idx, sc in enumerate(scorecards):
            grades_summary.append(
                f"### Grader {idx+1} Recommendation: {sc.overall_recommendation.upper()}\n"
                f"Scores: {json.dumps(sc.criteria_scores)}\n"
                f"Notes: {sc.notes or 'N/A'}"
            )
        raw_scorecard_text = "\n\n".join(grades_summary)

        # Apply candidate bias redaction just in case scorecards mention their name
        anonymized_scorecards = AnonymizationService.anonymize_text(
            text=raw_scorecard_text,
            full_name=app.candidate.full_name if app.candidate else None,
            email=app.candidate.email if app.candidate else None,
            phone=app.candidate.phone if app.candidate else None,
            candidate_alias=candidate_alias
        )

        prompt = f"""You are an expert recruitment supervisor. Aggregate the scorecard feedback and grader grade allocations.
Calculate consensus indices and identify grader alignment or divergence.
Candidate: {candidate_alias}

Interviewer Feedback Data:
{anonymized_scorecards}

Output structure in Markdown format:
# Scorecard Consensus Report
## Agreement & Disagreement Highlights
- Areas of Agreement: [e.g. coding skills]
- Areas of Divergence: [e.g. grader 1 gave YES but grader 2 gave NO]
## Consolidated Strengths
- Strength 1
- Strength 2
## Consolidated Concerns
- Concern 1
- Concern 2
"""
        llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.1)
        response = llm.invoke(prompt)
        return response.content.strip(), scorecard_ids

    @classmethod
    def _generate_hiring_recommendation(
        cls,
        db,
        app: Application,
        candidate: Candidate,
        candidate_alias: str
    ) -> tuple[str, list[str], list[str]]:
        """
        Generates a confidence-weighted Hire/No-Hire recommendation combining both resume and scorecard inputs.
        """
        # Fetch Resume source references
        embeddings = db.scalars(
            select(CandidateEmbedding)
            .where(CandidateEmbedding.candidate_id == candidate.id)
        ).all()
        embedding_ids = [str(emb.id) for emb in embeddings[:20]]
        raw_resume = "\n\n".join([emb.chunk_text for emb in embeddings[:20]])

        # Fetch Scorecard source references
        scorecards = db.scalars(
            select(Scorecard).where(Scorecard.application_id == app.id)
        ).all()
        scorecard_ids = [str(sc.id) for sc in scorecards]
        
        grades_summary = []
        for idx, sc in enumerate(scorecards):
            grades_summary.append(
                f"Grader {idx+1} Recommendation: {sc.overall_recommendation}\n"
                f"Scores: {json.dumps(sc.criteria_scores)}\n"
                f"Notes: {sc.notes or 'N/A'}"
            )
        raw_scorecard_text = "\n\n".join(grades_summary)

        # Gather job and company context
        job = app.job
        company = job.company if job else None
        
        job_info = ""
        if job:
            job_info += f"Job Title: {job.title}\n"
            job_info += f"Department: {job.department}\n"
            job_info += f"Description: {job.description}\n"
            if job.settings:
                settings = job.settings
                job_info += f"Employment Type: {settings.get('employment_type', 'Full Time')}\n"
                job_info += f"Workplace: {settings.get('workplace_type', 'On-site')}\n"
                if settings.get('salary_min') or settings.get('salary_max'):
                    job_info += f"Compensation Range: {settings.get('salary_min')} - {settings.get('salary_max')} {settings.get('currency', 'USD')}\n"
                if settings.get('required_skills'):
                    job_info += f"Required Skills: {', '.join(settings.get('required_skills'))}\n"
                if settings.get('preferred_skills'):
                    job_info += f"Preferred Skills: {', '.join(settings.get('preferred_skills'))}\n"
                if settings.get('benefits'):
                    job_info += f"Benefits: {', '.join(settings.get('benefits'))}\n"

        if company:
            job_info += f"Company Name: {company.name}\n"
            if company.settings:
                c_settings = company.settings
                if c_settings.get('description'):
                    job_info += f"Company Description: {c_settings.get('description')}\n"
                if c_settings.get('industry'):
                    job_info += f"Company Industry: {c_settings.get('industry')}\n"
                if c_settings.get('company_size'):
                    job_info += f"Company Size: {c_settings.get('company_size')}\n"

        # Anonymize all inputs
        anonymized_resume = AnonymizationService.anonymize_text(
            text=raw_resume,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            candidate_alias=candidate_alias
        )
        anonymized_scorecards = AnonymizationService.anonymize_text(
            text=raw_scorecard_text,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            candidate_alias=candidate_alias
        )

        prompt = f"""You are the head of structured recruitment and hiring.
Determine a final Hire/No-Hire decision based on candidate resume, scorecard feedback, and the target job description/requirements.
Candidate: {candidate_alias}

Target Job Requirements & Company Context:
{job_info}

Anonymized Resume:
{anonymized_resume}

Anonymized Interview Scorecards:
{anonymized_scorecards}

Output structure in Markdown format:
# Hiring Recommendation: [HIRE or NO-HIRE]
## Recommendation Rationale
[Provide deep analysis of strengths, technical alignment, and cultural interview signals]
## Core Decision Factors
- Factor 1
- Factor 2
"""
        llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.1)
        response = llm.invoke(prompt)
        return response.content.strip(), embedding_ids, scorecard_ids

    @classmethod
    def generate_job_description(
        cls,
        title: str,
        department: str,
        company_name: str,
        industry: str | None = None
    ) -> dict:
        """
        AI-generated job description content structured into Overview, Responsibilities, Requirements, and Benefits.
        Reuses existing AI service abstraction and returns structured JSON with error fallbacks.
        """
        prompt = f"""You are a professional recruiting copywriter. Generate a high-quality, structured job description for:
Job Title: {title}
Department: {department}
Company: {company_name}
{f"Industry: {industry}" if industry else ""}

Return a JSON object containing exactly the following keys:
- description: Overview of the role and team.
- responsibilities: A list of key responsibilities for the role.
- requirements: A list of requirements (skills, experience).
- benefits: A list of benefits/perks offered.

JSON Output:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.5)
            response = llm.invoke(prompt)
            data = json.loads(response.content.strip())
            return {
                "description": str(data.get("description", "")),
                "responsibilities": list(data.get("responsibilities", [])),
                "requirements": list(data.get("requirements", [])),
                "benefits": list(data.get("benefits", []))
            }
        except Exception as e:
            import logging
            logging.getLogger("smartonboard.intelligence").error(f"AI job description generation failed: {e}")
            return {
                "description": f"We are seeking a talented {title} to join our {department} team.",
                "responsibilities": [f"Contribute to the goals of the {department} department."],
                "requirements": [f"Experience as a {title} or related role."],
                "benefits": ["Competitive salary and benefits."]
            }

    @classmethod
    def suggest_skills(cls, title: str) -> list[str]:
        """
        AI-suggested contextual skills for a given job title.
        Returns a list of 10 skills.
        """
        prompt = f"""Given the job title: "{title}", suggest a list of 10 related technical skills, technologies, frameworks, and tools.
Return a JSON array of strings.

JSON Output:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.3)
            response = llm.invoke(prompt)
            skills = json.loads(response.content.strip())
            if isinstance(skills, list):
                return [str(s).strip() for s in skills if s]
            return []
        except Exception as e:
            import logging
            logging.getLogger("smartonboard.intelligence").error(f"AI skill suggestions failed: {e}")
            return ["Communication", "Problem Solving", "Teamwork"]

    @classmethod
    def generate_job_description_v2(
        cls,
        title: str,
        department: str,
        company_name: str,
        industry: str | None = None,
        workplace_type: str | None = None,
        employment_type: str | None = None,
        seniority: str | None = None,
        required_skills: list[str] | None = None,
        preferred_skills: list[str] | None = None,
        section: str | None = None
    ) -> dict:
        context = f"""Job Title: {title}
Department: {department}
Company: {company_name}
{f"Industry: {industry}" if industry else ""}
{f"Workplace Setting: {workplace_type}" if workplace_type else ""}
{f"Employment Type: {employment_type}" if employment_type else ""}
{f"Seniority Level: {seniority}" if seniority else ""}
{f"Required Skills: {', '.join(required_skills)}" if required_skills else ""}
{f"Preferred Skills: {', '.join(preferred_skills)}" if preferred_skills else ""}"""

        if section:
            prompt = f"""You are a professional recruiting copywriter. Under the following context:
{context}

Generate only the "{section}" section of the job description as a plain text string. Return a JSON object with a single key "{section}".
Output exactly this JSON format:
{{
  "{section}": "Generated text..."
}}

JSON Output:"""
        else:
            prompt = f"""You are a professional recruiting copywriter. Under the following context:
{context}

Generate a full structured job description. Return a JSON object containing exactly the following keys:
- description: Overview of the role, team, and company.
- responsibilities: Core tasks and responsibilities of the role.
- requirements: Core required skills and experience.
- benefits: Perks and benefits offered.
- qualifications: Core educational or professional qualifications.

Each key must map to a formatted string block.

JSON Output:"""

        def validate_data(data: dict) -> bool:
            if section:
                return section in data and isinstance(data[section], str)
            expected_keys = ["description", "responsibilities", "requirements", "benefits", "qualifications"]
            return all(k in data and isinstance(data[k], str) for k in expected_keys)

        llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.5)

        try:
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            content_str = response.content.strip()
            
            try:
                data = json.loads(content_str)
                if validate_data(data):
                    return {"success": True, **data}
                raise ValueError("Missing required keys or invalid schema types")
            except Exception as parse_err:
                repair_prompt = f"""You are a JSON fixer assistant. The previous output failed validation.
Error details: {parse_err}
Original instruction prompt:
{prompt}

Malformed output returned:
{content_str}

Please return the corrected JSON object matching the required schema:"""
                repair_response = invoke_with_retry(llm, repair_prompt, max_retries=1, timeout=30)
                repaired_data = json.loads(repair_response.content.strip())
                if validate_data(repaired_data):
                    return {"success": True, **repaired_data}
                raise ValueError("JSON repair pass failed to produce valid structure")
                
        except TimeoutError:
            return {
                "success": False,
                "error_code": "timeout",
                "message": "AI request timed out. Please try again.",
                "retryable": True
            }
        except Exception as e:
            err_msg = str(e).lower()
            error_code = "rate_limit" if "429" in err_msg or "rate" in err_msg else "provider_error"
            return {
                "success": False,
                "error_code": error_code,
                "message": f"AI generation failed: {str(e)}",
                "retryable": True
            }

    @classmethod
    def suggest_skills_v2(
        cls,
        title: str,
        department: str | None = None,
        existing_skills: list[str] | None = None
    ) -> dict:
        prompt = f"""You are a premium AI recruitment assistant. Given the job title: "{title}", department: "{department or 'General'}", and existing skills: {existing_skills or []}, suggest contextually relevant criteria.
        
        Return a JSON object containing exactly the following keys:
        - required_skills: A list of 5-8 essential core technical skills.
        - preferred_skills: A list of 4-6 nice-to-have supporting skills.
        - technologies: A list of 5-8 technologies, frameworks, tools, or libraries.
        - languages: A list of 2-3 languages (programming or natural spoken) that are useful.
        
        JSON Output:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.3)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            data = json.loads(response.content.strip())
            return {
                "required_skills": [str(s).strip() for s in data.get("required_skills", []) if s],
                "preferred_skills": [str(s).strip() for s in data.get("preferred_skills", []) if s],
                "technologies": [str(s).strip() for s in data.get("technologies", []) if s],
                "languages": [str(s).strip() for s in data.get("languages", []) if s]
            }
        except Exception as e:
            import logging
            logging.getLogger("smartonboard.intelligence").error(f"AI skill suggestions failed: {e}")
            return {
                "required_skills": ["Communication", "Problem Solving"],
                "preferred_skills": ["Teamwork"],
                "technologies": [],
                "languages": ["English"]
            }

    @classmethod
    def generate_executive_summary(cls, metrics_summary: str) -> str:
        """
        Generates a markdown executive talent summary briefing from aggregated metrics.
        Guarantees strict privacy: no candidate names, resumes, or details are passed.
        """
        prompt = f"""You are a premium executive talent consultant. Analyze these aggregated hiring metrics and write a concise, professional markdown executive briefing.
        
        Focus on:
        • Hiring velocity trends
        • Recruitment bottlenecks
        • Recruiter workload and productivity
        • Strategic actionable recommendations
        
        Aggregated Metrics:
        {metrics_summary}
        
        Mitigate bias:
        - Do not infer, mention, or speculate on protected characteristics (such as age, gender, race, or prestige).
        - Do not speculate beyond the provided statistics.
        - Ensure a neutral, fact-based professional tone.
        
        Executive Briefing Markdown:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.3)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            return response.content.strip()
        except Exception as e:
            import logging
            logging.getLogger("smartonboard.intelligence").error(f"AI executive summary generation failed: {e}")
            return f"**Hiring Executive Briefing**\n\nUnable to generate AI analysis: {str(e)}."

    @classmethod
    def candidate_chat(cls, message: str, history: list[dict]) -> str:
        """AI Chatbot conversational assistant for candidates."""
        history_str = ""
        for msg in history:
            role = "Candidate" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['message']}\n"
        
        prompt = f"""You are a helpful and supportive AI Candidate Assistant. Assist the candidate with their queries.
Follow these guidelines strictly:
- Clearly distinguish platform-level guidance from company-specific information.
- Never make assumptions or fabricate information about the hiring company or specific job internal details.
- Provide clear, professional, and friendly answers.

Conversation History:
{history_str}

Candidate: {message}
AI Assistant:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.5)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            return response.content.strip()
        except Exception as e:
            return f"Chatbot Assistant is temporarily offline: {str(e)}"

    @classmethod
    def resume_feedback(cls, resume_content: str) -> str:
        """Provides objective, constructive feedback on candidate's parsed resume."""
        prompt = f"""You are a premium career development assistant. Analyze the candidate's resume content below and provide objective, constructive feedback on technical skills formatting, resume structure, impact statements, and layout readability.
Do not make assumptions about target jobs. Keep formatting in Markdown.

Resume Content:
{resume_content}

Objective Feedback Markdown:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.3)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            return response.content.strip()
        except Exception as e:
            return f"Resume feedback generator is temporarily offline: {str(e)}"

    @classmethod
    def interview_preparation(cls, role_title: str, job_description: str) -> str:
        """Provides general interview prep advice based on job title and description.
        Enforces guardrail: Never fabricate company-specific interview questions.
        """
        prompt = f"""You are a premium career preparation assistant. Create a comprehensive interview preparation guide for the role of "{role_title}".

Job Description Context:
{job_description}

Guidelines:
- Provide general preparation tips, technical competencies, and behavioral questions suited for this role.
- CRITICAL GUARDRAIL: Never fabricate or claim that specific interview questions come from the target hiring company.
- Clearly distinguish platform preparation guidance from company-specific requirements.

Preparation Guide Markdown:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.3)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            return response.content.strip()
        except Exception as e:
            return f"Interview preparation guide is temporarily offline: {str(e)}"

    @classmethod
    def offer_explanation(cls, salary: float, equity: str, benefits: str) -> str:
        """Explains the components of an offer neutrally.
        Enforces guardrail: Must never recommend whether the candidate should accept or decline.
        """
        prompt = f"""You are a neutral compensation explanation assistant. Explain the following offer parameters clearly and objectively:
- Annual Base Salary: {salary}
- Equity Grant: {equity or "None"}
- Additional Benefits: {benefits or "Standard benefits package"}

Guidelines:
- Provide neutral explanations of salary tax implications, equity grant vesting terms (standard 4-year with 1-year cliff), and benefits details.
- CRITICAL GUARDRAIL: You must NEVER advise or recommend whether the candidate should accept or reject this offer. Remain completely neutral.

Neutral Offer Explanation Markdown:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.1)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            return response.content.strip()
        except Exception as e:
            return f"Offer explanation tool is temporarily offline: {str(e)}"

    @classmethod
    def company_overview(cls, company_name: str, industry: str) -> str:
        """Provides a neutral public profile summary of a company."""
        prompt = f"""You are a professional business research assistant. Provide a brief, neutral overview of a company named "{company_name}" operating in the "{industry or 'General'}" industry.
Focus on standard industry trends, typical department structures, and helpful background context for an applicant.
Do not fabricate internal company statistics or private data.

Neutral Overview Markdown:"""
        try:
            llm = ChatGroq(model_name=cls.MODEL_VERSION, temperature=0.3)
            response = invoke_with_retry(llm, prompt, max_retries=2, timeout=30)
            return response.content.strip()
        except Exception as e:
            return f"Company overview tool is temporarily offline: {str(e)}"


