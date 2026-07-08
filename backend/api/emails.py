import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import RequireRecruiter, TenantDb, RequireOwner
from models.email import EmailTemplate, SentEmail
from core.email_tracking import EmailTrackingService
from core.audit import log_audit_event

router = APIRouter(prefix="/emails", tags=["emails"])


class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body_markdown: str
    trigger_type: str | None = None


class EmailTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    subject: str
    body_markdown: str
    trigger_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class SentEmailResponse(BaseModel):
    id: uuid.UUID
    recipient: str
    subject: str
    status: str
    open_count: int
    click_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: EmailTemplateCreate,
    current_user: RequireRecruiter,
    db: TenantDb
):
    template = EmailTemplate(
        company_id=current_user.company_id,
        name=payload.name,
        subject=payload.subject,
        body_markdown=payload.body_markdown,
        trigger_type=payload.trigger_type
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    log_audit_event(
        db=db,
        action="email.template_created",
        actor_type="user",
        company_id=current_user.company_id,
        actor_id=current_user.id,
        resource_type="email_templates",
        resource_id=str(template.id)
    )
    return template


@router.get("/templates", response_model=List[EmailTemplateResponse])
def list_templates(
    current_user: RequireRecruiter,
    db: TenantDb
):
    stmt = select(EmailTemplate).where(EmailTemplate.company_id == current_user.company_id)
    templates = db.scalars(stmt).all()
    return list(templates)


@router.put("/templates/{template_id}", response_model=EmailTemplateResponse)
def update_template(
    template_id: uuid.UUID,
    payload: EmailTemplateCreate,
    current_user: RequireRecruiter,
    db: TenantDb
):
    template = db.scalar(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.company_id == current_user.company_id
        )
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    template.name = payload.name
    template.subject = payload.subject
    template.body_markdown = payload.body_markdown
    template.trigger_type = payload.trigger_type
    template.updated_at = datetime.now(timezone.utc)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    current_user: RequireRecruiter,
    db: TenantDb
):
    template = db.scalar(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.company_id == current_user.company_id
        )
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    db.delete(template)
    db.commit()
    return None


@router.get("/sent", response_model=List[SentEmailResponse])
def list_sent_emails(
    current_user: RequireRecruiter,
    db: TenantDb
):
    stmt = select(SentEmail).where(SentEmail.company_id == current_user.company_id).order_by(SentEmail.created_at.desc())
    emails = db.scalars(stmt).all()
    return list(emails)


@router.get("/public/track/open/{sent_email_id}")
def public_track_open(
    sent_email_id: uuid.UUID,
    db: TenantDb
):
    # No auth required since it is a public tracking pixel
    from db.session import tenant_context
    with tenant_context(auth_mode="true"):
        pixel_bytes = EmailTrackingService.track_open(db, sent_email_id)
    return Response(content=pixel_bytes, media_type="image/gif")


@router.get("/public/track/click/{sent_email_id}")
def public_track_click(
    sent_email_id: uuid.UUID,
    url: str,
    db: TenantDb
):
    from db.session import tenant_context
    from fastapi.responses import RedirectResponse
    with tenant_context(auth_mode="true"):
        redirect_url = EmailTrackingService.track_click(db, sent_email_id, url)
    return RedirectResponse(url=redirect_url)


@router.post("/public/webhooks/{provider}")
def public_email_webhook(
    provider: str,
    payload: dict,
    db: TenantDb
):
    from db.session import tenant_context
    with tenant_context(auth_mode="true"):
        EmailTrackingService.handle_webhook(db, provider, payload)
    return {"status": "processed"}

