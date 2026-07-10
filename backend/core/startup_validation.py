import os
import sys
import logging
from sqlalchemy import text
from db.session import SessionLocal
from core.redis_cache import get_redis_client

logger = logging.getLogger(__name__)


def validate_startup_connections() -> bool:
    """
    Validates connection health to critical backends (PostgreSQL, Redis) at boot time.
    Fails fast with sys.exit(1) if any critical resource is offline.
    """
    logger.info("Initializing startup checks...")
    
    # 1. Verify PostgreSQL Connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection validated successfully.")
    except Exception as e:
        logger.critical(f"FATAL: Database connection check failed: {e}")
        sys.exit(1)

    # 2. Verify Redis Cache Connection
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        logger.info("Redis cache connection validated successfully.")
    except Exception as e:
        logger.critical(f"FATAL: Redis connection check failed: {e}")
        sys.exit(1)

    logger.info("All infrastructure connections validated successfully.")
    return True
