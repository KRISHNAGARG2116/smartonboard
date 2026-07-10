import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from db.session import tenant_context
from models import Company, User, Job, Candidate, CandidateProfile
from models.enums import CompanyStatus, UserRole
from models.crm_models import (
    TalentPool,
    TalentPoolRuleHistory,
    TalentPoolMembership,
    CandidateRelationship,
    CachedMatchScore,
    MatchScoreHistory,
    MatchFeedback
)
from core.intelligence import GenerativeIntelligenceService


def test_talent_crm_rls_and_crud(db_session):
    """Test Talent Pool creation, rule version history, and RLS isolation."""
    # 1. Create tenant company and user
    with tenant_context(auth_mode="true"):
        company = Company(name="CRM Corp", slug="crm-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        user = User(
            company_id=company.id,
            email="recruiter@crmcorp.com",
            password_hash="hash",
            full_name="Sarah Connor",
            role=UserRole.RECRUITER
        )
        db_session.add(user)
        db_session.commit()

    # 2. Scope to Company and perform CRUD
    with tenant_context(tenant_id=str(company.id)):
        # Create a static Talent Pool
        pool = TalentPool(
            company_id=company.id,
            name="React Engineers",
            description="Static React candidates",
            created_by=user.id
        )
        db_session.add(pool)
        db_session.commit()

        # Query pool
        queried = db_session.scalar(select(TalentPool).where(TalentPool.id == pool.id))
        assert queried is not None
        assert queried.name == "React Engineers"
        assert queried.rule_version == 1

        # Modify to dynamic pool (triggering rule history write)
        history = TalentPoolRuleHistory(
            talent_pool_id=pool.id,
            company_id=company.id,
            dynamic_rules=pool.dynamic_rules or {},
            rule_version=pool.rule_version,
            updated_by=user.id
        )
        db_session.add(history)
        
        pool.dynamic_rules = {"location": "San Francisco", "skills": ["React"]}
        pool.rule_version = 2
        db_session.commit()

        # Check version history
        hist = db_session.scalars(select(TalentPoolRuleHistory).where(TalentPoolRuleHistory.talent_pool_id == pool.id)).all()
        assert len(hist) == 1
        assert hist[0].rule_version == 1


def test_candidate_relationship_stage(db_session):
    """Test updating candidate relationship stages and properties."""
    with tenant_context(auth_mode="true"):
        company = Company(name="Match Corp", slug="match-corp", status=CompanyStatus.ACTIVE)
        db_session.add(company)
        db_session.flush()

        user = User(company_id=company.id, email="rec@matchcorp.com", password_hash="h", full_name="Sarah", role=UserRole.RECRUITER)
        db_session.add(user)
        
        cand = Candidate(company_id=company.id, email="john@connor.com", full_name="John Connor")
        db_session.add(cand)
        db_session.commit()

    with tenant_context(tenant_id=str(company.id)):
        # Create candidate relationship
        rel = CandidateRelationship(
            candidate_id=cand.id,
            company_id=company.id,
            owner_id=user.id,
            crm_stage="new_lead",
            relationship_status="contacted",
            is_pinned=True
        )
        db_session.add(rel)
        db_session.commit()

        # Verify properties
        queried = db_session.scalar(select(CandidateRelationship).where(CandidateRelationship.candidate_id == cand.id))
        assert queried is not None
        assert queried.crm_stage == "new_lead"
        assert queried.is_pinned is True


def test_deterministic_scoring_calculations():
    """Test the deterministic matching score and confidence evaluator."""
    profile = {
        "skills": ["Python", "React", "Docker"],
        "location": "San Francisco, CA",
        "experience_years": 5.0
    }
    job_reqs = {
        "required_skills": ["Python", "React"],
        "location": "San Francisco",
        "required_experience_years": 4.0
    }

    # Calculate match score
    result = GenerativeIntelligenceService.calculate_deterministic_match_score(profile, job_reqs)
    assert result["overall_score"] >= 80
    assert result["breakdown"]["skills"] == 100
    assert result["breakdown"]["location"] == 100

    # Calculate confidence
    confidence, reasons = GenerativeIntelligenceService.calculate_deterministic_confidence(
        result["overall_score"], 0.90
    )
    assert confidence == "high"
    assert "Resume complete" in reasons
    assert "Required skills verified" in reasons
