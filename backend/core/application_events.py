import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from models.ats_models import ApplicationEvent


class ApplicationEventService:
    @staticmethod
    def record_event(
        db: Session,
        company_id: uuid.UUID,
        application_id: uuid.UUID,
        event_type: str,
        actor_id: uuid.UUID | None = None,
        actor_name: str | None = None,
        previous_value: str | None = None,
        new_value: str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> ApplicationEvent:
        """
        Creates and stores an immutable timeline event for an application.
        All timeline events are append-only.
        """
        # Automatically resolve actor name if not provided
        if actor_id and not actor_name:
            from models import User
            from sqlalchemy import select
            user = db.scalar(select(User).where(User.id == actor_id))
            if user:
                actor_name = user.full_name

        meta = dict(metadata) if metadata else {}
        meta.update({
            "company_id": str(company_id),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "previous_value": previous_value,
            "new_value": new_value,
        })

        event = ApplicationEvent(
            application_id=application_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_name=actor_name,
            metadata_json=meta,
        )
        db.add(event)
        db.flush()
        return event
