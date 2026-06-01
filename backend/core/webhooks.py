import logging
from tasks.webhooks import dispatch_webhook_event_task

logger = logging.getLogger("app")


def trigger_webhook_event(company_id: str, event_type: str, payload: dict):
    """
    Unified platform entrypoint to publish event dispatches asynchronously to Celery workers.
    """
    try:
        dispatch_webhook_event_task.delay(str(company_id), event_type, payload)
        logger.info(f"Successfully enqueued async webhook task for event: {event_type} (Company: {company_id})")
    except Exception as e:
        logger.error(f"Failed to enqueue webhook task for event: {event_type}. Error: {str(e)}")
