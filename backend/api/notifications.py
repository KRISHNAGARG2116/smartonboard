import uuid
import logging
from datetime import datetime, timezone
from typing import Annotated, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update

from api.deps import TenantDb, CurrentUser
from models.ats_models import Notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])

# Simple mock storage for user notification preferences in-memory fallback
NOTIFICATION_PREFERENCES: Dict[str, Dict[str, Any]] = {}


class BulkReadRequest(BaseModel):
    notification_ids: List[uuid.UUID] | None = None  # None means mark all as read


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool
    in_app_enabled: bool
    digest_enabled: bool
    muted_categories: List[str]


@router.get("")
def list_notifications(
    db: TenantDb,
    current_user: CurrentUser,
    status_filter: str | None = None
):
    """Retrieves all notification listings for the authenticated recruiter."""
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    
    stmt = stmt.order_by(Notification.created_at.desc())
    results = db.scalars(stmt).all()

    return [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "status": n.status,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else datetime.now(timezone.utc).isoformat()
        }
        for n in results
    ]


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: uuid.UUID,
    db: TenantDb,
    current_user: CurrentUser
):
    """Marks a single notification as read."""
    n = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")

    n.status = "read"
    n.read_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "id": str(n.id)}


@router.post("/bulk-read")
def bulk_mark_notifications_read(
    payload: BulkReadRequest,
    db: TenantDb,
    current_user: CurrentUser
):
    """Bulk marks notifications as read."""
    stmt = update(Notification).where(Notification.user_id == current_user.id)
    
    if payload.notification_ids is not None:
        stmt = stmt.where(Notification.id.in_(payload.notification_ids))
        
    stmt = stmt.values(status="read", read_at=datetime.now(timezone.utc))
    db.execute(stmt)
    db.commit()

    return {"status": "success"}


@router.get("/preferences")
def get_notification_preferences(current_user: CurrentUser):
    """Retrieves notification delivery preferences."""
    user_id_str = str(current_user.id)
    if user_id_str not in NOTIFICATION_PREFERENCES:
        # Default preferences
        return {
            "email_enabled": True,
            "in_app_enabled": True,
            "digest_enabled": False,
            "muted_categories": []
        }
    return NOTIFICATION_PREFERENCES[user_id_str]


@router.put("/preferences")
def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: CurrentUser
):
    """Updates notification channels and muting matrices."""
    user_id_str = str(current_user.id)
    preferences = {
        "email_enabled": payload.email_enabled,
        "in_app_enabled": payload.in_app_enabled,
        "digest_enabled": payload.digest_enabled,
        "muted_categories": payload.muted_categories
    }
    NOTIFICATION_PREFERENCES[user_id_str] = preferences
    return {"status": "success", "preferences": preferences}
