import uuid
from sqlalchemy.orm import Session
from models.ats_models import ApplicationEvent


def log_application_event(
    db: Session,
    application_id: uuid.UUID,
    event_type: str,
    actor_id: uuid.UUID | None = None,
    actor_name: str | None = None,
    metadata: dict = None,
):
    """
    Creates and logs an immutable timeline event for an application.
    """
    event = ApplicationEvent(
        application_id=application_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_name=actor_name,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.flush()
    return event
