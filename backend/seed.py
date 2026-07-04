import sys
import os
import uuid
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, delete, text

# Add backend directory to python import path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import get_settings
from db.session import SessionLocal, tenant_context
from core.security import hash_password
from models import Company, User, Job, Candidate, Application, Interview
from models.enums import CompanyStatus, VerificationState, TrustLevel, UserRole, AuthProvider, JobStatus, ApplicationStatus

# Check optional models
try:
    from models.scorecard import Scorecard
    has_scorecard_model = True
except ImportError:
    has_scorecard_model = False

try:
    from models.note import CandidateNote
    has_note_model = True
except ImportError:
    has_note_model = False

settings = get_settings()

# Environment Guard
env = os.getenv("ENV", "development").lower()
fastapi_env = os.getenv("FASTAPI_ENV", "development").lower()
if env == "production" or fastapi_env == "production" or "production" in settings.database_url:
    raise ValueError("Terminal Error: Seed script cannot be run in a production environment!")


def get_company_verification_fields():
    """Inspect existing Company model attributes to safely verify verification fields at run-time."""
    fields = {}
    for attr in [
        "verification_state",
        "trust_level",
        "domain_verified",
        "website_verified",
        "identity_verified",
        "is_verified_company",
        "is_verified_recruiter",
        "is_trusted_employer",
    ]:
        if hasattr(Company, attr):
            if attr == "verification_state":
                fields[attr] = VerificationState.VERIFIED_COMPANY
            elif attr == "trust_level":
                fields[attr] = TrustLevel.TRUSTED_EMPLOYER
            else:
                fields[attr] = True
    return fields


def clean_demo_tenant(db):
    """Clean the seeded company and all cascading child records under the RLS bypass context."""
    print("Cleaning existing demo company 'smartonboard-demo'...")
    db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', false)"))
    stmt = select(Company).where(Company.slug == "smartonboard-demo")
    company = db.scalar(stmt)
    if company:
        db.delete(company)
        db.commit()
        print("Demo company and child records successfully deleted.")
    else:
        print("No existing demo company found to clean.")


from models.stage_transition import CandidateStageTransition
from models.funnel_aggregate import FunnelAggregate


def track_transition(db, company_id, application_id, job_id, from_status, to_status, transitioned_at, duration_seconds=None):
    trans = CandidateStageTransition(
        company_id=company_id,
        application_id=application_id,
        from_status=from_status,
        to_status=to_status,
        transitioned_at=transitioned_at,
        duration_seconds=duration_seconds
    )
    db.add(trans)
    db.flush()

    if to_status:
        agg_stmt = select(FunnelAggregate).where(
            FunnelAggregate.company_id == company_id,
            FunnelAggregate.job_id == job_id,
            FunnelAggregate.stage == to_status
        )
        agg_to = db.scalar(agg_stmt)
        if not agg_to:
            agg_to = FunnelAggregate(
                company_id=company_id,
                job_id=job_id,
                stage=to_status,
                candidate_count=1,
                conversion_count=0
            )
            db.add(agg_to)
        else:
            agg_to.candidate_count += 1
        db.flush()

    if from_status and to_status != "rejected" and to_status != from_status:
        agg_from_stmt = select(FunnelAggregate).where(
            FunnelAggregate.company_id == company_id,
            FunnelAggregate.job_id == job_id,
            FunnelAggregate.stage == from_status
        )
        agg_from = db.scalar(agg_from_stmt)
        if not agg_from:
            agg_from = FunnelAggregate(
                company_id=company_id,
                job_id=job_id,
                stage=from_status,
                candidate_count=1,
                conversion_count=1
            )
            db.add(agg_from)
        else:
            agg_from.conversion_count += 1
        db.flush()


def seed_application_history(db, company_id, application_id, job_id, status, created_time):
    if status == ApplicationStatus.SUBMITTED:
        track_transition(db, company_id, application_id, job_id, "", "submitted", created_time)
    elif status == ApplicationStatus.SCREENING:
        t1 = created_time - timedelta(days=2)
        track_transition(db, company_id, application_id, job_id, "", "submitted", t1)
        track_transition(db, company_id, application_id, job_id, "submitted", "screening", created_time, 86400 * 2)
    elif status == ApplicationStatus.INTERVIEW:
        t1 = created_time - timedelta(days=5)
        t2 = created_time - timedelta(days=3)
        track_transition(db, company_id, application_id, job_id, "", "submitted", t1)
        track_transition(db, company_id, application_id, job_id, "submitted", "screening", t2, 86400 * 2)
        track_transition(db, company_id, application_id, job_id, "screening", "interview", created_time, 86400 * 3)
    elif status == ApplicationStatus.OFFER:
        t1 = created_time - timedelta(days=8)
        t2 = created_time - timedelta(days=6)
        t3 = created_time - timedelta(days=3)
        track_transition(db, company_id, application_id, job_id, "", "submitted", t1)
        track_transition(db, company_id, application_id, job_id, "submitted", "screening", t2, 86400 * 2)
        track_transition(db, company_id, application_id, job_id, "screening", "interview", t3, 86400 * 3)
        track_transition(db, company_id, application_id, job_id, "interview", "offer", created_time, 86400 * 3)
    elif status == ApplicationStatus.HIRED:
        t1 = created_time - timedelta(days=11)
        t2 = created_time - timedelta(days=9)
        t3 = created_time - timedelta(days=6)
        t4 = created_time - timedelta(days=3)
        track_transition(db, company_id, application_id, job_id, "", "submitted", t1)
        track_transition(db, company_id, application_id, job_id, "submitted", "screening", t2, 86400 * 2)
        track_transition(db, company_id, application_id, job_id, "screening", "interview", t3, 86400 * 3)
        track_transition(db, company_id, application_id, job_id, "interview", "offer", t4, 86400 * 3)
        track_transition(db, company_id, application_id, job_id, "offer", "hired", created_time, 86400 * 3)
    elif status == ApplicationStatus.REJECTED:
        t1 = created_time - timedelta(days=4)
        t2 = created_time - timedelta(days=2)
        track_transition(db, company_id, application_id, job_id, "", "submitted", t1)
        track_transition(db, company_id, application_id, job_id, "submitted", "screening", t2, 86400 * 2)
        track_transition(db, company_id, application_id, job_id, "screening", "rejected", created_time, 86400 * 2)


def seed_demo_tenant(db):
    """Seed a realistic recruiter development tenant with 3 jobs, 9 applications, scorecards, and notes."""
    print("Seeding demo company...")
    db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', false)"))

    # 1. Seed or Update Company
    stmt = select(Company).where(Company.slug == "smartonboard-demo")
    company = db.scalar(stmt)
    verification_fields = get_company_verification_fields()

    if not company:
        company = Company(
            name="SmartOnboard Demo Company",
            slug="smartonboard-demo",
            status=CompanyStatus.ACTIVE,
            settings={},
            **verification_fields
        )
        db.add(company)
        db.flush()
    else:
        company.name = "SmartOnboard Demo Company"
        company.status = CompanyStatus.ACTIVE
        for k, v in verification_fields.items():
            setattr(company, k, v)
        db.flush()

    company_id = company.id
    print(f"Company ID: {company_id}")

    # Clear existing transitions and aggregates for this company to prevent duplicate counting during updates
    db.execute(delete(CandidateStageTransition).where(CandidateStageTransition.company_id == company_id))
    db.execute(delete(FunnelAggregate).where(FunnelAggregate.company_id == company_id))
    db.flush()

    # 2. Seed or Update Recruiter User
    user_email = "recruiter.demo@smartonboard.com"
    user_stmt = select(User).where(User.email == user_email)
    user = db.scalar(user_stmt)

    if not user:
        user = User(
            company_id=company_id,
            email=user_email,
            password_hash=hash_password("Recruiter123!"),
            full_name="Demo Recruiter",
            role=UserRole.RECRUITER,
            is_active=True,
            email_verified=True,
            auth_provider=AuthProvider.LOCAL,
        )
        db.add(user)
        db.flush()
    else:
        user.company_id = company_id
        user.full_name = "Demo Recruiter"
        user.password_hash = hash_password("Recruiter123!")
        user.is_active = True
        user.email_verified = True
        db.flush()

    recruiter_id = user.id
    print(f"Recruiter ID: {recruiter_id}")

    # 3. Seed or Update Jobs
    jobs_data = [
        {
            "title": "Senior Full Stack Engineer",
            "department": "Engineering",
            "description": "Seeking a backend engineer skilled in FastAPI, SQL, and Celery.",
        },
        {
            "title": "Product Manager",
            "department": "Product",
            "description": "Drive product strategy and recruiter workflows.",
        },
        {
            "title": "Security Analyst",
            "department": "Security",
            "description": "Enforce network controls and verify identity signals.",
        },
    ]

    jobs = []
    for jd in jobs_data:
        j_stmt = select(Job).where(Job.company_id == company_id, Job.title == jd["title"])
        job = db.scalar(j_stmt)
        if not job:
            job = Job(
                company_id=company_id,
                title=jd["title"],
                department=jd["department"],
                description=jd["description"],
                status=JobStatus.OPEN,
                settings={},
            )
            db.add(job)
            db.flush()
        else:
            job.department = jd["department"]
            job.description = jd["description"]
            job.status = JobStatus.OPEN
            db.flush()
        jobs.append(job)

    # 4. Seed Candidates & Applications spread across realistic stages and timestamps
    candidates_data = [
        {
            "name": "Alice Cooper",
            "email": "alice@cooper.net",
            "status": ApplicationStatus.HIRED,
            "days_ago": 15,
            "resume": "Alice is a senior fullstack engineer with 8 years of Python/FastAPI experience. Expert in React UI design.",
        },
        {
            "name": "Bob Marley",
            "email": "bob@marley.net",
            "status": ApplicationStatus.HIRED,
            "days_ago": 15,
            "resume": "Bob is a seasoned Product Manager. Experienced in driving B2B SaaS recruiter workflows and user metrics.",
        },
        {
            "name": "Charlie Brown",
            "email": "charlie@brown.org",
            "status": ApplicationStatus.OFFER,
            "days_ago": 8,
            "resume": "Charlie is a backend specialist. Focuses on SQL tuning, Docker containerization, and REST API performance.",
        },
        {
            "name": "Diana Ross",
            "email": "diana@ross.com",
            "status": ApplicationStatus.INTERVIEW,
            "days_ago": 5,
            "resume": "Diana Ross. Expert in asynchronous task processing using Celery and Redis. Skilled in backend FastAPI scaling.",
        },
        {
            "name": "Elvis Presley",
            "email": "elvis@presley.com",
            "status": ApplicationStatus.INTERVIEW,
            "days_ago": 5,
            "resume": "Elvis Presley. Focuses on security audits, access control validation, and identity verification compliance systems.",
        },
        {
            "name": "Frank Sinatra",
            "email": "frank@sinatra.com",
            "status": ApplicationStatus.SCREENING,
            "days_ago": 3,
            "resume": "Frank Sinatra. Software engineer with 3 years of backend experience. Familiar with Python scripting and Node web APIs.",
        },
        {
            "name": "Grace Kelly",
            "email": "grace@kelly.edu",
            "status": ApplicationStatus.SUBMITTED,
            "days_ago": 1,
            "resume": "Grace Kelly. Frontend developer specialized in React, CSS flexbox, TypeScript typing, and accessibility design.",
        },
        {
            "name": "Hank Williams",
            "email": "hank@williams.net",
            "status": ApplicationStatus.SUBMITTED,
            "days_ago": 1,
            "resume": "Hank Williams. Associate Product Manager with Figma layout skills, roadmapping experience, and user research interviews.",
        },
        {
            "name": "Iris Murdoch",
            "email": "iris@murdoch.org",
            "status": ApplicationStatus.REJECTED,
            "days_ago": 12,
            "resume": "Iris Murdoch. Ruby on Rails developer with basic scripting skills. Looking for backend jobs.",
        },
    ]

    from core.embeddings import EmbeddingService
    embedder = EmbeddingService()

    # Map candidates to jobs
    job_mapping = {
        "Alice Cooper": jobs[0],
        "Charlie Brown": jobs[0],
        "Diana Ross": jobs[0],
        "Frank Sinatra": jobs[0],
        "Grace Kelly": jobs[0],
        "Iris Murdoch": jobs[0],
        "Bob Marley": jobs[1],
        "Hank Williams": jobs[1],
        "Elvis Presley": jobs[2],
    }

    # Verify if GROQ_API_KEY is configured
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    if not has_groq:
        print("Note: GROQ_API_KEY is absent. Generating mock pipeline metrics locally.")

    for cd in candidates_data:
        c_stmt = select(Candidate).where(Candidate.company_id == company_id, Candidate.email == cd["email"])
        candidate = db.scalar(c_stmt)
        if not candidate:
            candidate = Candidate(
                company_id=company_id,
                email=cd["email"],
                full_name=cd["name"],
                phone="555-0100",
            )
            db.add(candidate)
            db.flush()
        else:
            candidate.full_name = cd["name"]
            db.flush()

        target_job = job_mapping[cd["name"]]
        created_time = datetime.now(timezone.utc) - timedelta(days=cd["days_ago"])

        # Idempotency: Clean existing embeddings
        from models import CandidateEmbedding
        db.execute(delete(CandidateEmbedding).where(
            CandidateEmbedding.company_id == company_id,
            CandidateEmbedding.candidate_id == candidate.id
        ))
        db.flush()

        # Seed local HuggingFace embeddings programmatically
        chunks = [cd["resume"]]
        for idx, chunk in enumerate(chunks):
            vector = embedder.generate_embedding(chunk)
            emb = CandidateEmbedding(
                company_id=company_id,
                candidate_id=candidate.id,
                resume_embedding=vector,
                chunk_text=chunk,
                chunk_index=idx,
                embedding_provider="huggingface",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_version=1,
            )
            db.add(emb)
        db.flush()

        # Calculate similarity score programmatically
        job_desc_vector = embedder.generate_embedding(target_job.description or target_job.title)
        cand_emb_vector = embedder.generate_embedding(cd["resume"])
        score = embedder.compute_similarity(job_desc_vector, cand_emb_vector)
        match_percentage = round(score * 100, 2)

        # Seed Application
        app_stmt = select(Application).where(Application.job_id == target_job.id, Application.candidate_id == candidate.id)
        application = db.scalar(app_stmt)
        if not application:
            application = Application(
                company_id=company_id,
                job_id=target_job.id,
                candidate_id=candidate.id,
                status=cd["status"],
                source="seeder",
                match_score=float(match_percentage),
                created_at=created_time,
                updated_at=created_time,
            )
            db.add(application)
            db.flush()
        else:
            application.status = cd["status"]
            application.match_score = float(match_percentage)
            application.created_at = created_time
            application.updated_at = created_time
            db.flush()

        # Seed realistic stage transition history and aggregates for analytics
        seed_application_history(db, company_id, application.id, target_job.id, cd["status"], created_time)

        # 5. Create Interview (for interview stage candidates)
        if cd["status"] == ApplicationStatus.INTERVIEW:
            sched_days = 0 if cd["name"] == "Diana Ross" else -1
            scheduled_time = datetime.now(timezone.utc) + timedelta(days=sched_days, hours=2)

            int_stmt = select(Interview).where(Interview.application_id == application.id)
            interview = db.scalar(int_stmt)
            if not interview:
                interview = Interview(
                    company_id=company_id,
                    application_id=application.id,
                    interviewer_id=recruiter_id,
                    title=f"Technical Interview - {cd['name']}",
                    stage="Technical",
                    scheduled_at=scheduled_time,
                    duration_minutes=45,
                    video_link="https://meet.google.com/abc-defg-hij",
                    is_cancelled=False,
                    created_at=created_time,
                )
                db.add(interview)
                db.flush()
            else:
                interview.scheduled_at = scheduled_time
                interview.interviewer_id = recruiter_id
                db.flush()

            # 6. Seed Scorecards if model exists
            if has_scorecard_model:
                sc_stmt = select(Scorecard).where(Scorecard.interview_id == interview.id)
                scorecard = db.scalar(sc_stmt)
                if not scorecard:
                    scorecard = Scorecard(
                        company_id=company_id,
                        application_id=application.id,
                        interview_id=interview.id,
                        grader_id=recruiter_id,
                        criteria_scores={"coding": 4, "communication": 5, "architecture": 4},
                        overall_recommendation="strong_yes" if cd["name"] == "Diana Ross" else "yes",
                        notes="Seeded feedback note: Candidate demonstrated clear knowledge of B2B SaaS requirements.",
                        submitted_at=scheduled_time + timedelta(minutes=60),
                        created_at=scheduled_time + timedelta(minutes=60),
                    )
                    db.add(scorecard)
                    db.flush()
                else:
                    scorecard.grader_id = recruiter_id
                    db.flush()

        # 7. Seed Recruiter Notes if model exists
        if has_note_model and cd["name"] in ["Alice Cooper", "Charlie Brown"]:
            note_stmt = select(CandidateNote).where(CandidateNote.application_id == application.id)
            note = db.scalar(note_stmt)
            if not note:
                note = CandidateNote(
                    company_id=company_id,
                    application_id=application.id,
                    user_id=recruiter_id,
                    content=f"Review note: {cd['name']} is highly recommended.",
                    created_at=created_time + timedelta(hours=4),
                )
                db.add(note)
                db.flush()
            else:
                note.content = f"Review note: {cd['name']} is highly recommended."
                db.flush()

    db.commit()
    print("Demo tenant seeded successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed recruiter development tenant.")
    parser.add_argument("--clean", action="store_true", help="Delete the seeded company and all child records.")
    parser.add_argument("--reset", action="store_true", help="Clean first, then re-seed.")
    args = parser.parse_args()

    with tenant_context(auth_mode="true"):
        db_session = SessionLocal()
        try:
            if args.clean or args.reset:
                clean_demo_tenant(db_session)

            if not args.clean:
                seed_demo_tenant(db_session)
        finally:
            db_session.close()
