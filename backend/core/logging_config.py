import logging
import os
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    env = os.getenv("ENV", "development").lower()
    fastapi_env = os.getenv("FASTAPI_ENV", "development").lower()
    is_production = (env == "production") or (fastapi_env == "production")
    
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    
    if is_production:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d'
        )
        # Ensure log level is INFO or higher in production
        root_logger.setLevel(logging.INFO)
        # Prevent double-logging when running FastAPI/Uvicorn or Celery
        logging.getLogger("uvicorn.access").propagate = False
        logging.getLogger("uvicorn.error").propagate = False
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        root_logger.setLevel(logging.DEBUG)
        
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def log_performance_metric(name: str, duration_ms: float, metadata: dict = None):
    """
    Utility to write structured performance/latency metric logs
    that can be easily parsed by log aggregation tools (Datadog, Kibana, etc.).
    """
    logger = logging.getLogger("metrics")
    extra_fields = {
        "metric_event": True,
        "metric_name": name,
        "duration_ms": duration_ms
    }
    if metadata:
        extra_fields.update(metadata)
    logger.info(f"Performance metric trace: {name}", extra=extra_fields)
