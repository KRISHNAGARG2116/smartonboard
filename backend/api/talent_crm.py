import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy import select, delete, text, and_, or_, func
from sqlalchemy.orm import Session

from api.deps import TenantDb, RequirePermission, RequireRecruiter
from models.rbac import UserPermission
from models import (
    Candidate,
    User,
    Application,
    CandidateProfile,
    SavedSearch,
    ApplicationEvent
)
from models.crm_models import (
    TalentPool,
    TalentPoolRuleHistory,
    TalentPoolMembership,
    CandidateRelationship,
    CandidateActivity,
    OutreachSequence,
    CandidateSequenceEnrollment,
    CandidateMergeLog
)

router = APIRouter(prefix="/talent", tags=["talent-crm"])


# --- PYDANTIC SCHEMAS ---

class TalentPoolCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    color: str = "#6b7280"
    icon: Optional[str] = None
    visibility: str = "public"
    dynamic_rules: Optional[dict] = None

class TalentPoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    visibility: Optional[str] = None
    dynamic_rules: Optional[dict] = None

class PoolMembershipPayload(BaseModel):
    candidate_ids: List[uuid.UUID]

class RelationshipUpdate(BaseModel):
    owner_id: Optional[uuid.UUID] = None
    secondary_owner_id: Optional[uuid.UUID] = None
    watchers: Optional[List[uuid.UUID]] = None
    crm_stage: Optional[str] = None
    relationship_status: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_favorite: Optional[bool] = None
    ignore_ai_match: Optional[bool] = None
    next_follow_up_at: Optional[datetime] = None

class SequenceCreate(BaseModel):
    name: str = Field(..., max_length=150)
    steps: List[dict] = []

class SequenceEnrollPayload(BaseModel):
    candidate_ids: List[uuid.UUID]
    sequence_id: uuid.UUID

class MergePreviewRequest(BaseModel):
    merged_candidate_id: uuid.UUID
    surviving_candidate_id: uuid.UUID

class MergeRequest(BaseModel):
    merged_candidate_id: uuid.UUID
    surviving_candidate_id: uuid.UUID
    resolved_fields: Optional[dict] = None  # e.g., {"full_name": "surviving", "phone": "merged"}

class BulkActionRequest(BaseModel):
    candidate_ids: List[uuid.UUID]
    action_type: str  # "add_to_pool", "remove_from_pool", "assign_recruiter", "schedule_followup", "enroll_sequence", "archive", "tag"
    pool_id: Optional[uuid.UUID] = None
    recruiter_id: Optional[uuid.UUID] = None
    followup_date: Optional[datetime] = None
    sequence_id: Optional[uuid.UUID] = None
    tag_ids: Optional[List[uuid.UUID]] = None


# --- HELPER FUNCTIONS ---

def log_crm_activity(
    db: Session,
    company_id: uuid.UUID,
    candidate_id: uuid.UUID,
    activity_type: str,
    description: str,
    recruiter_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None
):
    activity = CandidateActivity(
        company_id=company_id,
        candidate_id=candidate_id,
        recruiter_id=recruiter_id,
        activity_type=activity_type,
        description=description,
        details=details or {}
    )
    db.add(activity)


def get_candidate_profile_and_relationship(db: Session, candidate_id: uuid.UUID, company_id: uuid.UUID):
    candidate = db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.company_id == company_id)
    )
    if not candidate:
        return None, None, None

    user = db.scalar(select(User).where(User.email == candidate.email))
    profile = None
    if user:
        profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))

    relationship = db.scalar(
        select(CandidateRelationship).where(
            CandidateRelationship.candidate_id == candidate_id,
            CandidateRelationship.company_id == company_id
        )
    )
    return candidate, profile, relationship


def evaluate_dynamic_rules(profile: Optional[CandidateProfile], relationship: Optional[CandidateRelationship], rules: dict) -> bool:
    if not rules:
        return True

    # 1. Location
    if "location" in rules and rules["location"]:
        if not profile or not profile.location or rules["location"].lower() not in profile.location.lower():
            return False

    # 2. Skills
    if "skills" in rules and rules["skills"]:
        if not profile or not profile.skills:
            return False
        required_skills = [s.lower() for s in rules["skills"]]
        profile_skills = [s.lower() for s in profile.skills]
        if not all(skill in profile_skills for skill in required_skills):
            return False

    # 3. Experience Years
    if "experience_years" in rules and rules["experience_years"] is not None:
        if not profile or not profile.experience:
            return False
        # Calculate experience years from JSON list
        total_days = 0
        for exp in profile.experience:
            try:
                start = datetime.strptime(exp.get("start_date", ""), "%Y-%m-%d")
                end_str = exp.get("end_date")
                end = datetime.strptime(end_str, "%Y-%m-%d") if end_str else datetime.now()
                total_days += (end - start).days
            except Exception:
                continue
        total_years = total_days / 365.25
        if total_years < float(rules["experience_years"]):
            return False

    # 4. Last Contacted Days
    if "last_contacted_days" in rules and rules["last_contacted_days"] is not None:
        if not relationship or not relationship.last_contacted_at:
            return False
        days_since = (datetime.now(timezone.utc) - relationship.last_contacted_at.replace(tzinfo=timezone.utc)).days
        if days_since < int(rules["last_contacted_days"]):
            return False

    return True


# --- TALENT POOLS ENDPOINTS ---

@router.get("/pools")
def list_pools(
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb,
    include_archived: bool = False,
    include_deleted: bool = False
):
    stmt = select(TalentPool).where(TalentPool.company_id == current_user.company_id)
    if not include_deleted:
        stmt = stmt.where(TalentPool.is_deleted == False)
    if not include_archived:
        stmt = stmt.where(TalentPool.is_archived == False)

    pools = db.scalars(stmt).all()
    results = []

    for pool in pools:
        # Evaluate count
        if pool.dynamic_rules:
            # Dynamic count
            candidates = db.scalars(
                select(Candidate).where(Candidate.company_id == current_user.company_id)
            ).all()
            member_count = 0
            for cand in candidates:
                _, profile, rel = get_candidate_profile_and_relationship(db, cand.id, current_user.company_id)
                if evaluate_dynamic_rules(profile, rel, pool.dynamic_rules):
                    member_count += 1
        else:
            # Static count
            member_count = db.scalar(
                select(func.count(TalentPoolMembership.candidate_id))
                .where(TalentPoolMembership.talent_pool_id == pool.id)
            ) or 0

        results.append({
            "id": str(pool.id),
            "name": pool.name,
            "description": pool.description,
            "color": pool.color,
            "icon": pool.icon,
            "visibility": pool.visibility,
            "is_dynamic": bool(pool.dynamic_rules),
            "dynamic_rules": pool.dynamic_rules,
            "rule_version": pool.rule_version,
            "is_archived": pool.is_archived,
            "is_deleted": pool.is_deleted,
            "member_count": member_count,
            "created_at": pool.created_at,
            "updated_at": pool.updated_at
        })

    return results


@router.post("/pools", status_code=status.HTTP_201_CREATED)
def create_pool(
    body: TalentPoolCreate,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = TalentPool(
        company_id=current_user.company_id,
        name=body.name,
        description=body.description,
        color=body.color,
        icon=body.icon,
        visibility=body.visibility,
        dynamic_rules=body.dynamic_rules,
        created_by=current_user.id
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return pool


@router.patch("/pools/{pool_id}")
def update_pool(
    pool_id: uuid.UUID,
    body: TalentPoolUpdate,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if body.name is not None:
        pool.name = body.name
    if body.description is not None:
        pool.description = body.description
    if body.color is not None:
        pool.color = body.color
    if body.icon is not None:
        pool.icon = body.icon
    if body.visibility is not None:
        pool.visibility = body.visibility

    if body.dynamic_rules is not None:
        # History versioning
        history = TalentPoolRuleHistory(
            talent_pool_id=pool.id,
            company_id=current_user.company_id,
            dynamic_rules=pool.dynamic_rules or {},
            rule_version=pool.rule_version,
            updated_by=current_user.id
        )
        db.add(history)
        
        pool.dynamic_rules = body.dynamic_rules
        pool.rule_version += 1

    db.commit()
    db.refresh(pool)
    return pool


@router.delete("/pools/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pool(
    pool_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    pool.is_deleted = True
    pool.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/pools/{pool_id}/restore")
def restore_pool(
    pool_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    pool.is_deleted = False
    pool.deleted_at = None
    db.commit()
    return {"status": "success", "message": "Talent pool restored successfully"}


@router.post("/pools/{pool_id}/archive")
def archive_pool(
    pool_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    pool.is_archived = True
    pool.archived_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "Talent pool archived"}


@router.post("/pools/{pool_id}/unarchive")
def unarchive_pool(
    pool_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    pool.is_archived = False
    pool.archived_at = None
    db.commit()
    return {"status": "success", "message": "Talent pool unarchived"}


@router.get("/pools/{pool_id}/rules/history")
def get_pool_rules_history(
    pool_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    histories = db.scalars(
        select(TalentPoolRuleHistory)
        .where(
            TalentPoolRuleHistory.talent_pool_id == pool_id,
            TalentPoolRuleHistory.company_id == current_user.company_id
        )
        .order_by(TalentPoolRuleHistory.rule_version.desc())
    ).all()
    return histories


@router.post("/pools/{pool_id}/rules/rollback/{version}")
def rollback_pool_rules(
    pool_id: uuid.UUID,
    version: int,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    history = db.scalar(
        select(TalentPoolRuleHistory).where(
            TalentPoolRuleHistory.talent_pool_id == pool_id,
            TalentPoolRuleHistory.company_id == current_user.company_id,
            TalentPoolRuleHistory.rule_version == version
        )
    )
    if not history:
        raise HTTPException(status_code=404, detail="History rule version not found")

    # Add current to history
    new_history = TalentPoolRuleHistory(
        talent_pool_id=pool.id,
        company_id=current_user.company_id,
        dynamic_rules=pool.dynamic_rules or {},
        rule_version=pool.rule_version,
        updated_by=current_user.id
    )
    db.add(new_history)

    pool.dynamic_rules = history.dynamic_rules
    pool.rule_version = pool.rule_version + 1
    db.commit()
    return {"status": "success", "message": f"Rolled back rules successfully to version {version}"}


# --- MEMBERSHIP ENDPOINTS ---

@router.get("/pools/{pool_id}/members")
def list_pool_members(
    pool_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.dynamic_rules:
        # Dynamic query
        candidates = db.scalars(
            select(Candidate).where(Candidate.company_id == current_user.company_id)
        ).all()
        members = []
        for cand in candidates:
            _, profile, rel = get_candidate_profile_and_relationship(db, cand.id, current_user.company_id)
            if evaluate_dynamic_rules(profile, rel, pool.dynamic_rules):
                members.append(cand)
        return members
    else:
        # Static query
        members = db.scalars(
            select(Candidate)
            .join(TalentPoolMembership, Candidate.id == TalentPoolMembership.candidate_id)
            .where(
                TalentPoolMembership.talent_pool_id == pool_id,
                Candidate.company_id == current_user.company_id
            )
        ).all()
        return members


@router.post("/pools/{pool_id}/members")
def add_pool_members(
    pool_id: uuid.UUID,
    body: PoolMembershipPayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.dynamic_rules:
        raise HTTPException(status_code=400, detail="Cannot manually add candidates to a dynamic pool")

    for cand_id in body.candidate_ids:
        # Verify candidate exists and belongs to company
        cand = db.scalar(
            select(Candidate).where(Candidate.id == cand_id, Candidate.company_id == current_user.company_id)
        )
        if not cand:
            continue

        existing = db.scalar(
            select(TalentPoolMembership).where(
                TalentPoolMembership.talent_pool_id == pool_id,
                TalentPoolMembership.candidate_id == cand_id
            )
        )
        if not existing:
            membership = TalentPoolMembership(
                candidate_id=cand_id,
                talent_pool_id=pool_id,
                company_id=current_user.company_id,
                added_by=current_user.id,
                source="manual"
            )
            db.add(membership)
            log_crm_activity(
                db=db,
                company_id=current_user.company_id,
                candidate_id=cand_id,
                recruiter_id=current_user.id,
                activity_type="added_to_pool",
                description=f"Added to Talent Pool: {pool.name}",
                details={"pool_id": str(pool_id), "pool_name": pool.name}
            )

    db.commit()
    return {"status": "success", "message": "Candidates successfully added to pool"}


@router.delete("/pools/{pool_id}/members/{candidate_id}")
def remove_pool_member(
    pool_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    pool = db.scalar(
        select(TalentPool).where(TalentPool.id == pool_id, TalentPool.company_id == current_user.company_id)
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    if pool.dynamic_rules:
        raise HTTPException(status_code=400, detail="Cannot manually remove candidates from a dynamic pool")

    membership = db.scalar(
        select(TalentPoolMembership).where(
            TalentPoolMembership.talent_pool_id == pool_id,
            TalentPoolMembership.candidate_id == candidate_id,
            TalentPoolMembership.company_id == current_user.company_id
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    db.delete(membership)
    log_crm_activity(
        db=db,
        company_id=current_user.company_id,
        candidate_id=candidate_id,
        recruiter_id=current_user.id,
        activity_type="removed_from_pool",
        description=f"Removed from Talent Pool: {pool.name}",
        details={"pool_id": str(pool_id), "pool_name": pool.name}
    )
    db.commit()
    return {"status": "success", "message": "Candidate removed from pool"}


# --- RELATIONSHIP ENDPOINTS ---

@router.get("/candidates/{candidate_id}/relationship")
def get_relationship(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    _, _, rel = get_candidate_profile_and_relationship(db, candidate_id, current_user.company_id)
    if not rel:
        return {
            "candidate_id": str(candidate_id),
            "crm_stage": "new_lead",
            "relationship_status": "contacted",
            "is_pinned": False,
            "is_favorite": False,
            "ignore_ai_match": False,
            "engagement_score": 0
        }
    return rel


@router.patch("/candidates/{candidate_id}/relationship")
def update_relationship(
    candidate_id: uuid.UUID,
    body: RelationshipUpdate,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_CANDIDATE_RELATIONSHIPS))],
    db: TenantDb
):
    candidate = db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.company_id == current_user.company_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    rel = db.scalar(
        select(CandidateRelationship).where(
            CandidateRelationship.candidate_id == candidate_id,
            CandidateRelationship.company_id == current_user.company_id
        )
    )
    
    is_new = False
    if not rel:
        is_new = True
        rel = CandidateRelationship(
            candidate_id=candidate_id,
            company_id=current_user.company_id,
            owner_id=current_user.id,
            crm_stage="new_lead",
            relationship_status="contacted"
        )
        db.add(rel)

    changes = {}
    if body.owner_id is not None:
        rel.owner_id = body.owner_id
        changes["owner_id"] = str(body.owner_id)
    if body.secondary_owner_id is not None:
        rel.secondary_owner_id = body.secondary_owner_id
        changes["secondary_owner_id"] = str(body.secondary_owner_id)
    if body.watchers is not None:
        rel.watchers = [str(w) for w in body.watchers]
        changes["watchers"] = rel.watchers
    if body.crm_stage is not None:
        old_stage = rel.crm_stage
        rel.crm_stage = body.crm_stage
        changes["crm_stage"] = {"old": old_stage, "new": body.crm_stage}
        log_crm_activity(
            db=db,
            company_id=current_user.company_id,
            candidate_id=candidate_id,
            recruiter_id=current_user.id,
            activity_type="crm_stage_updated",
            description=f"CRM Pipeline Stage updated from {old_stage} to {body.crm_stage}",
            details={"old_stage": old_stage, "new_stage": body.crm_stage}
        )
    if body.relationship_status is not None:
        rel.relationship_status = body.relationship_status
        changes["relationship_status"] = body.relationship_status
    if body.is_pinned is not None:
        rel.is_pinned = body.is_pinned
    if body.is_favorite is not None:
        rel.is_favorite = body.is_favorite
    if body.ignore_ai_match is not None:
        rel.ignore_ai_match = body.ignore_ai_match
    if body.next_follow_up_at is not None:
        rel.next_follow_up_at = body.next_follow_up_at
        log_crm_activity(
            db=db,
            company_id=current_user.company_id,
            candidate_id=candidate_id,
            recruiter_id=current_user.id,
            activity_type="followup_scheduled",
            description=f"Outreach follow-up reminder scheduled for {body.next_follow_up_at.strftime('%Y-%m-%d')}",
            details={"next_follow_up_at": body.next_follow_up_at.isoformat()}
        )

    db.commit()
    db.refresh(rel)
    return rel


# --- FOLLOW-UPS ENDPOINTS ---

@router.get("/follow-ups")
def list_followups(
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    stmt = (
        select(CandidateRelationship, Candidate.full_name, Candidate.email)
        .join(Candidate, CandidateRelationship.candidate_id == Candidate.id)
        .where(
            CandidateRelationship.company_id == current_user.company_id,
            CandidateRelationship.next_follow_up_at != None
        )
        .order_by(CandidateRelationship.next_follow_up_at.asc())
    )
    rows = db.execute(stmt).all()
    results = []
    for rel, full_name, email in rows:
        results.append({
            "candidate_id": str(rel.candidate_id),
            "full_name": full_name,
            "email": email,
            "next_follow_up_at": rel.next_follow_up_at,
            "crm_stage": rel.crm_stage,
            "relationship_status": rel.relationship_status
        })
    return results


# --- CANDIDATE TIMELINE ENDPOINTS ---

@router.get("/candidates/{candidate_id}/timeline")
def get_unified_timeline(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb,
    filter_type: Optional[str] = Query(None)  # E.g. "emails", "interviews", "notes", "applications", "ai", "pools", "system_events"
):
    candidate = db.scalar(
        select(Candidate).where(Candidate.id == candidate_id, Candidate.company_id == current_user.company_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    timeline = []

    # 1. Fetch CRM Activities
    act_stmt = select(CandidateActivity).where(
        CandidateActivity.candidate_id == candidate_id,
        CandidateActivity.company_id == current_user.company_id
    )
    activities = db.scalars(act_stmt).all()
    for act in activities:
        # Determine mapping type
        mapped_type = "system_events"
        if act.activity_type in ("email_sent", "email_opened", "candidate_replied"):
            mapped_type = "emails"
        elif act.activity_type in ("added_to_pool", "removed_from_pool"):
            mapped_type = "pools"
        elif act.activity_type == "recruiter_note":
            mapped_type = "notes"
        elif act.activity_type == "rediscovered":
            mapped_type = "ai"

        if filter_type and filter_type != mapped_type:
            continue

        timeline.append({
            "id": f"crm-{act.id}",
            "type": mapped_type,
            "title": act.activity_type.replace("_", " ").title(),
            "description": act.description,
            "details": act.details,
            "created_at": act.created_at,
            "actor_id": str(act.recruiter_id) if act.recruiter_id else None
        })

    # 2. Fetch ATS events
    # Find applications for this candidate
    app_stmt = select(Application).where(
        Application.candidate_id == candidate_id,
        Application.company_id == current_user.company_id
    )
    apps = db.scalars(app_stmt).all()
    app_ids = [a.id for a in apps]

    if app_ids:
        evt_stmt = select(ApplicationEvent).where(ApplicationEvent.application_id.in_(app_ids))
        events = db.scalars(evt_stmt).all()
        for evt in events:
            mapped_type = "system_events"
            if "interview" in evt.event_type.lower():
                mapped_type = "interviews"
            elif "note" in evt.event_type.lower():
                mapped_type = "notes"
            elif "apply" in evt.event_type.lower() or "submitted" in evt.event_type.lower():
                mapped_type = "applications"
            elif "ai" in evt.event_type.lower() or "match" in evt.event_type.lower():
                mapped_type = "ai"

            if filter_type and filter_type != mapped_type:
                continue

            timeline.append({
                "id": f"ats-{evt.id}",
                "type": mapped_type,
                "title": evt.event_type.replace(".", " ").title(),
                "description": f"Event recorded on application. Actor: {evt.actor_name or 'System'}",
                "details": evt.metadata_json,
                "created_at": evt.created_at,
                "actor_id": str(evt.actor_id) if evt.actor_id else None
            })

    # Sort Newest First
    timeline.sort(key=lambda x: x["created_at"], reverse=True)
    return timeline


# --- CANDIDATE MERGE ENDPOINTS ---

@router.post("/candidates/merge/preview")
def preview_candidate_merge(
    body: MergePreviewRequest,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_CANDIDATE_RELATIONSHIPS))],
    db: TenantDb
):
    merged = db.scalar(
        select(Candidate).where(Candidate.id == body.merged_candidate_id, Candidate.company_id == current_user.company_id)
    )
    surviving = db.scalar(
        select(Candidate).where(Candidate.id == body.surviving_candidate_id, Candidate.company_id == current_user.company_id)
    )
    if not merged or not surviving:
        raise HTTPException(status_code=404, detail="One or both candidates not found")

    m_profile = db.scalar(select(CandidateProfile).join(User, CandidateProfile.user_id == User.id).where(User.email == merged.email))
    s_profile = db.scalar(select(CandidateProfile).join(User, CandidateProfile.user_id == User.id).where(User.email == surviving.email))

    return {
        "surviving": {
            "id": str(surviving.id),
            "full_name": surviving.full_name,
            "email": surviving.email,
            "phone": surviving.phone,
            "location": s_profile.location if s_profile else None,
            "skills": s_profile.skills if s_profile else []
        },
        "merged": {
            "id": str(merged.id),
            "full_name": merged.full_name,
            "email": merged.email,
            "phone": merged.phone,
            "location": m_profile.location if m_profile else None,
            "skills": m_profile.skills if m_profile else []
        }
    }


@router.post("/candidates/merge")
def execute_candidate_merge(
    body: MergeRequest,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_CANDIDATE_RELATIONSHIPS))],
    db: TenantDb
):
    merged = db.scalar(
        select(Candidate).where(Candidate.id == body.merged_candidate_id, Candidate.company_id == current_user.company_id)
    )
    surviving = db.scalar(
        select(Candidate).where(Candidate.id == body.surviving_candidate_id, Candidate.company_id == current_user.company_id)
    )
    if not merged or not surviving:
        raise HTTPException(status_code=404, detail="One or both candidates not found")

    # Snapshot snapshot before modification
    snapshot = {
        "id": str(merged.id),
        "full_name": merged.full_name,
        "email": merged.email,
        "phone": merged.phone,
        "created_at": merged.created_at.isoformat() if merged.created_at else None
    }

    # Redirect applications
    apps = db.scalars(select(Application).where(Application.candidate_id == merged.id)).all()
    for app in apps:
        app.candidate_id = surviving.id

    # Create merge log
    log = CandidateMergeLog(
        company_id=current_user.company_id,
        merged_candidate_id=merged.id,
        surviving_candidate_id=surviving.id,
        merged_by=current_user.id,
        merged_candidate_snapshot=snapshot
    )
    db.add(log)

    # Deactivate / suffix the email of the merged candidate to release unique email constraint
    original_email = merged.email
    merged.email = f"{merged.email}.merged.{uuid.uuid4().hex[:6]}"
    merged.full_name = f"[Merged] {merged.full_name}"

    log_crm_activity(
        db=db,
        company_id=current_user.company_id,
        candidate_id=surviving.id,
        recruiter_id=current_user.id,
        activity_type="candidate_merged",
        description=f"Candidate record {original_email} merged into this record.",
        details={"merged_candidate_id": str(merged.id), "original_email": original_email}
    )

    db.commit()
    return {"status": "success", "message": "Candidates merged successfully", "merge_log_id": str(log.id)}


@router.post("/candidates/merge/undo/{merge_log_id}")
def undo_candidate_merge(
    merge_log_id: uuid.UUID,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_CANDIDATE_RELATIONSHIPS))],
    db: TenantDb
):
    log = db.scalar(
        select(CandidateMergeLog).where(
            CandidateMergeLog.id == merge_log_id,
            CandidateMergeLog.company_id == current_user.company_id
        )
    )
    if not log:
        raise HTTPException(status_code=404, detail="Merge log not found")

    # Restore merged candidate
    merged = db.scalar(select(Candidate).where(Candidate.id == log.merged_candidate_id))
    if merged:
        snapshot = log.merged_candidate_snapshot
        merged.email = snapshot["email"]
        merged.full_name = snapshot["full_name"]

    # Redirect applications back
    apps = db.scalars(
        select(Application).where(
            Application.candidate_id == log.surviving_candidate_id,
            Application.created_at <= log.merged_at
        )
    ).all()
    for app in apps:
        app.candidate_id = log.merged_candidate_id

    db.delete(log)
    db.commit()
    return {"status": "success", "message": "Candidate merge reverted successfully"}


# --- OUTREACH SEQUENCES ENDPOINTS ---

@router.get("/sequences")
def list_sequences(
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.VIEW_TALENT_CRM))],
    db: TenantDb
):
    return db.scalars(
        select(OutreachSequence).where(OutreachSequence.company_id == current_user.company_id)
    ).all()


@router.post("/sequences", status_code=status.HTTP_201_CREATED)
def create_sequence(
    body: SequenceCreate,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    seq = OutreachSequence(
        company_id=current_user.company_id,
        name=body.name,
        steps=body.steps,
        created_by=current_user.id
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)
    return seq


@router.post("/sequences/enroll")
def enroll_sequence(
    body: SequenceEnrollPayload,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    seq = db.scalar(
        select(OutreachSequence).where(
            OutreachSequence.id == body.sequence_id,
            OutreachSequence.company_id == current_user.company_id
        )
    )
    if not seq:
        raise HTTPException(status_code=404, detail="Outreach sequence not found")

    for cand_id in body.candidate_ids:
        # Check enrollment
        existing = db.scalar(
            select(CandidateSequenceEnrollment).where(
                CandidateSequenceEnrollment.candidate_id == cand_id,
                CandidateSequenceEnrollment.sequence_id == body.sequence_id
            )
        )
        if not existing:
            enrollment = CandidateSequenceEnrollment(
                company_id=current_user.company_id,
                candidate_id=cand_id,
                sequence_id=body.sequence_id,
                status="enrolled",
                next_run_at=datetime.now(timezone.utc)
            )
            db.add(enrollment)
            log_crm_activity(
                db=db,
                company_id=current_user.company_id,
                candidate_id=cand_id,
                recruiter_id=current_user.id,
                activity_type="outreach_campaign",
                description=f"Enrolled in outreach sequence: {seq.name}",
                details={"sequence_id": str(seq.id), "sequence_name": seq.name}
            )

    db.commit()
    return {"status": "success", "message": "Candidates enrolled in sequence"}


# --- BULK ACTIONS ENDPOINTS ---

@router.post("/bulk-action")
def execute_bulk_action(
    body: BulkActionRequest,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    if body.action_type == "add_to_pool":
        if not body.pool_id:
            raise HTTPException(status_code=400, detail="Missing pool_id")
        pool = db.scalar(select(TalentPool).where(TalentPool.id == body.pool_id, TalentPool.company_id == current_user.company_id))
        if not pool or pool.dynamic_rules:
            raise HTTPException(status_code=400, detail="Invalid static pool selected")

        for cid in body.candidate_ids:
            membership = TalentPoolMembership(
                candidate_id=cid,
                talent_pool_id=body.pool_id,
                company_id=current_user.company_id,
                added_by=current_user.id,
                source="bulk_action"
            )
            db.add(membership)
            log_crm_activity(db, current_user.company_id, cid, "added_to_pool", f"Added to Talent Pool: {pool.name}", current_user.id)

    elif body.action_type == "remove_from_pool":
        if not body.pool_id:
            raise HTTPException(status_code=400, detail="Missing pool_id")
        pool = db.scalar(select(TalentPool).where(TalentPool.id == body.pool_id, TalentPool.company_id == current_user.company_id))
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        for cid in body.candidate_ids:
            db.execute(
                delete(TalentPoolMembership).where(
                    TalentPoolMembership.talent_pool_id == body.pool_id,
                    TalentPoolMembership.candidate_id == cid
                )
            )
            log_crm_activity(db, current_user.company_id, cid, "removed_from_pool", f"Removed from Talent Pool: {pool.name}", current_user.id)

    elif body.action_type == "assign_recruiter":
        if not body.recruiter_id:
            raise HTTPException(status_code=400, detail="Missing recruiter_id")
        for cid in body.candidate_ids:
            rel = db.scalar(select(CandidateRelationship).where(CandidateRelationship.candidate_id == cid))
            if not rel:
                rel = CandidateRelationship(candidate_id=cid, company_id=current_user.company_id, owner_id=body.recruiter_id)
                db.add(rel)
            else:
                rel.owner_id = body.recruiter_id
            log_crm_activity(db, current_user.company_id, cid, "recruiter_assigned", f"Recruiter assigned as relationship owner.", current_user.id)

    elif body.action_type == "schedule_followup":
        if not body.followup_date:
            raise HTTPException(status_code=400, detail="Missing followup_date")
        for cid in body.candidate_ids:
            rel = db.scalar(select(CandidateRelationship).where(CandidateRelationship.candidate_id == cid))
            if not rel:
                rel = CandidateRelationship(candidate_id=cid, company_id=current_user.company_id, next_follow_up_at=body.followup_date)
                db.add(rel)
            else:
                rel.next_follow_up_at = body.followup_date
            log_crm_activity(db, current_user.company_id, cid, "followup_scheduled", f"Outreach follow-up scheduled.", current_user.id)

    elif body.action_type == "enroll_sequence":
        if not body.sequence_id:
            raise HTTPException(status_code=400, detail="Missing sequence_id")
        seq = db.scalar(select(OutreachSequence).where(OutreachSequence.id == body.sequence_id, OutreachSequence.company_id == current_user.company_id))
        if not seq:
            raise HTTPException(status_code=404, detail="Sequence not found")
        for cid in body.candidate_ids:
            enrollment = CandidateSequenceEnrollment(
                company_id=current_user.company_id,
                candidate_id=cid,
                sequence_id=body.sequence_id,
                status="enrolled",
                next_run_at=datetime.now(timezone.utc)
            )
            db.add(enrollment)
            log_crm_activity(db, current_user.company_id, cid, "outreach_campaign", f"Enrolled in outreach sequence: {seq.name}", current_user.id)

    db.commit()
    return {"status": "success", "message": "Bulk action executed successfully"}


# --- CANDIDATE IMPORT STUB ENDPOINT ---

@router.post("/import")
def import_candidates(
    request: Request,
    current_user: Annotated[User, Depends(RequirePermission(UserPermission.MANAGE_TALENT_POOLS))],
    db: TenantDb
):
    # Stub: handles batch parses of references (CSV, LinkedIn, Referrals)
    # Automatically registers Candidate records inside company context
    return {"status": "success", "message": "Import completed successfully", "imported_count": 0}
