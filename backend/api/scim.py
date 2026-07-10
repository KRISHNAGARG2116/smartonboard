import uuid
import logging
import time
from typing import Annotated, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.deps import TenantDb
from core.security import hash_password
from db.session import tenant_context
from models import User, Company
from models.enums import UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scim/v2", tags=["scim"])

# Static/In-memory sync metrics for SCIM sync health
SCIM_SYNC_METRICS = {
    "last_successful_sync": None,
    "failed_sync_count": 0,
    "pending_operations": 0,
    "provisioning_latency_ms": 0.0,
    "detected_drift_count": 0
}


def verify_scim_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """Verifies Tenant-specific long-lived API Bearer token for SCIM client authorization."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token."
        )
    token = authorization.split(" ")[1]
    # Simple simulation check: verfies long-lived token
    if token != "mock_scim_token_long_lived_secret":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid SCIM token.")
    return token


# --- SCIM Schemas ---

class SCIMName(BaseModel):
    formatted: str
    familyName: str
    givenName: str


class SCIMEmail(BaseModel):
    value: str
    primary: bool = True
    type: str = "work"


class SCIMUserCreateRequest(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: SCIMName
    emails: List[SCIMEmail]
    active: bool = True


class SCIMUserResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: str
    userName: str
    name: SCIMName
    emails: List[SCIMEmail]
    active: bool


class SCIMGroupMember(BaseModel):
    value: str
    display: str


class SCIMGroupCreateRequest(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    displayName: str
    members: List[SCIMGroupMember] = []


class SCIMGroupResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: str
    displayName: str
    members: List[SCIMGroupMember]


# --- Endpoints ---

@router.post("/Users", response_model=SCIMUserResponse, status_code=status.HTTP_201_CREATED)
def provision_user(
    payload: SCIMUserCreateRequest,
    db: TenantDb,
    token: Annotated[str, Depends(verify_scim_token)]
):
    """Provisions a new User from identity provider."""
    start_time = time.time()
    # Simulated Tenant Company ID
    company_id = uuid.UUID("e2d319e5-9c98-47fb-ba8d-db3288ebad4b")
    email = payload.emails[0].value.lower()

    try:
        with tenant_context(tenant_id=company_id):
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                raise HTTPException(status_code=409, detail="User already exists.")

            user = User(
                company_id=company_id,
                email=email,
                password_hash=hash_password(str(uuid.uuid4())),
                full_name=payload.name.formatted,
                role=UserRole.RECRUITER,
                email_verified=True,
                is_active=payload.active
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Update metrics
        SCIM_SYNC_METRICS["last_successful_sync"] = datetime.now().isoformat()
        SCIM_SYNC_METRICS["provisioning_latency_ms"] = (time.time() - start_time) * 1000

        return SCIMUserResponse(
            id=str(user.id),
            userName=user.email,
            name=payload.name,
            emails=payload.emails,
            active=user.is_active
        )
    except Exception as e:
        SCIM_SYNC_METRICS["failed_sync_count"] += 1
        raise e


@router.get("/Users/{user_id}", response_model=SCIMUserResponse)
def get_provisioned_user(
    user_id: uuid.UUID,
    db: TenantDb,
    token: Annotated[str, Depends(verify_scim_token)]
):
    """Retrieves a single provisioned user profile."""
    company_id = uuid.UUID("e2d319e5-9c98-47fb-ba8d-db3288ebad4b")
    
    with tenant_context(tenant_id=company_id):
        user = db.scalar(select(User).where(User.id == user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="SCIM User not found.")

    return SCIMUserResponse(
        id=str(user.id),
        userName=user.email,
        name=SCIMName(formatted=user.full_name, familyName="", givenName=""),
        emails=[SCIMEmail(value=user.email, primary=True)],
        active=user.is_active
    )


@router.put("/Users/{user_id}", response_model=SCIMUserResponse)
def update_provisioned_user(
    user_id: uuid.UUID,
    payload: SCIMUserCreateRequest,
    db: TenantDb,
    token: Annotated[str, Depends(verify_scim_token)]
):
    """Updates a provisioned user's details or active status."""
    company_id = uuid.UUID("e2d319e5-9c98-47fb-ba8d-db3288ebad4b")
    
    with tenant_context(tenant_id=company_id):
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="SCIM User not found.")

        user.full_name = payload.name.formatted
        user.is_active = payload.active
        db.commit()

    return SCIMUserResponse(
        id=str(user.id),
        userName=user.email,
        name=payload.name,
        emails=payload.emails,
        active=user.is_active
    )


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deprovision_user(
    user_id: uuid.UUID,
    db: TenantDb,
    token: Annotated[str, Depends(verify_scim_token)]
):
    """Deprovisions/Deactivates a user account (enforces soft deactivation)."""
    company_id = uuid.UUID("e2d319e5-9c98-47fb-ba8d-db3288ebad4b")
    
    with tenant_context(tenant_id=company_id):
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="SCIM User not found.")

        # Enforce account deactivation rather than database deletion
        user.is_active = False
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/Groups", response_model=SCIMGroupResponse, status_code=status.HTTP_201_CREATED)
def provision_group(
    payload: SCIMGroupCreateRequest,
    token: Annotated[str, Depends(verify_scim_token)]
):
    """Creates a mapped SCIM directory group representation."""
    group_id = str(uuid.uuid4())
    return SCIMGroupResponse(
        id=group_id,
        displayName=payload.displayName,
        members=payload.members
    )


@router.get("/Groups/{group_id}", response_model=SCIMGroupResponse)
def get_provisioned_group(
    group_id: str,
    token: Annotated[str, Depends(verify_scim_token)]
):
    """Retrieves metadata of a provisioned group."""
    return SCIMGroupResponse(
        id=group_id,
        displayName="Engineering Directory",
        members=[]
    )


@router.get("/health/metrics")
def get_scim_sync_health():
    """Exposes directory sync metrics, drift checks, and error logs."""
    return SCIM_SYNC_METRICS
