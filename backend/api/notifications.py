import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select

from api.deps import TenantDb, RequireRecruiter
from models.ats_models import Notification
from schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: TenantDb,
    current_user: RequireRecruiter,
    status_filter: str | None = Query(default=None, alias="status"),
):
    """
    Lists all notifications for the authenticated recruiter, optionally filtered by status.
    """
    stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.company_id == current_user.company_id
    )
    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    else:
        # Default: exclude archived and dismissed unless explicitly queried
        stmt = stmt.where(Notification.status.in_(["unread", "read"]))

    stmt = stmt.order_by(Notification.created_at.desc())
    return db.scalars(stmt).all()


@router.post("/read-all")
def mark_all_notifications_read(
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Marks all unread notifications for the current recruiter as read.
    """
    from sqlalchemy import update
    now = datetime.now(timezone.utc)
    db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.company_id == current_user.company_id,
            Notification.status == "unread"
        )
        .values(status="read", read_at=now)
    )
    db.commit()
    return {"status": "success", "message": "All notifications marked as read"}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Marks a notification as read.
    """
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.company_id == current_user.company_id
        )
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.status = "read"
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/{notification_id}/archive", response_model=NotificationResponse)
def archive_notification(
    notification_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Marks a notification as archived.
    """
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.company_id == current_user.company_id
        )
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.status = "archived"
    notification.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
def dismiss_notification(
    notification_id: uuid.UUID,
    db: TenantDb,
    current_user: RequireRecruiter,
):
    """
    Dismisses a notification.
    """
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.company_id == current_user.company_id
        )
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.status = "dismissed"
    db.commit()
    db.refresh(notification)
    return notification
