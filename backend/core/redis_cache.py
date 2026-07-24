import json
import time
import asyncio
import logging
from functools import wraps
from typing import List, Dict, Any, Callable
import redis

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def get_redis_client():
    """Returns the singleton Redis client instance."""
    return redis_client

# Metrics tracking
CACHE_METRICS = {
    "hits": 0,
    "misses": 0,
    "lock_waits": 0,
    "lock_timeouts": 0
}


def _get_serializable_repr(val: Any) -> Any:
    """Safely converts arguments to serializable representations for key generation."""
    if isinstance(val, (str, int, float, bool, type(None))):
        return val
    if isinstance(val, (list, tuple, set)):
        return [_get_serializable_repr(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _get_serializable_repr(v) for k, v in val.items()}
    # Extract IDs for SQLAlchemy models or objects
    if hasattr(val, 'id'):
        return str(val.id)
    # Skip DB session
    if hasattr(val, 'connection') or hasattr(val, 'execute'):
        return None
    return str(val)


class RedisCacheService:

    @classmethod
    def get_metrics(cls) -> Dict[str, int]:
        return CACHE_METRICS

    @classmethod
    def set_value(cls, key: str, value: Any, ttl: int = 300, tags: List[str] = None):
        """Set a value in cache and map it to invalidation tags."""
        serialized = json.dumps(value)
        redis_client.setex(key, ttl, serialized)
        
        if tags:
            for tag in tags:
                # Add cache key to the tag's tracking set
                redis_client.sadd(f"tag_set:{tag}", key)
                # Keep tracking set alive slightly longer than key
                redis_client.expire(f"tag_set:{tag}", ttl + 3600)

    @classmethod
    def get_value(cls, key: str) -> Any | None:
        """Fetch value from cache."""
        val = redis_client.get(key)
        if val:
            CACHE_METRICS["hits"] += 1
            return json.loads(val)
        CACHE_METRICS["misses"] += 1
        return None

    @classmethod
    def invalidate_tags(cls, tags: List[str]):
        """Delete all keys registered under the given tags."""
        if not tags:
            return
            
        keys_to_delete = set()
        for tag in tags:
            tag_key = f"tag_set:{tag}"
            associated_keys = redis_client.smembers(tag_key)
            if associated_keys:
                keys_to_delete.update(associated_keys)
            # Cleanup the tag set itself
            keys_to_delete.add(tag_key)

        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            logger.info(f"Invalidated {len(keys_to_delete)} keys for tags {tags}")


def cached(namespace: str, ttl: int = 300, tags: List[str] = None):
    """
    Caching decorator with stampede locking (SingleFlight) protection.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Formulate cache key
            repr_args = [_get_serializable_repr(a) for a in args]
            repr_kwargs = {k: _get_serializable_repr(v) for k, v in kwargs.items()}
            arg_str = str(repr_args) + str(sorted(repr_kwargs.items()))
            cache_key = f"cache:{namespace}:{hash(arg_str)}"
            
            # 1. Attempt standard fetch
            cached_val = RedisCacheService.get_value(cache_key)
            if cached_val is not None:
                return cached_val

            # 2. Cache stampede protection: Acquire lock
            lock_key = f"lock:{cache_key}"
            lock_acquired = redis_client.set(lock_key, "locked", ex=10, nx=True)

            if lock_acquired:
                try:
                    # Execute task
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    # Save to cache
                    RedisCacheService.set_value(cache_key, result, ttl=ttl, tags=tags)
                    return result
                finally:
                    # Release lock
                    redis_client.delete(lock_key)
            else:
                # Lock is held: poll and wait for value to populate
                CACHE_METRICS["lock_waits"] += 1
                for _ in range(30):  # 3 seconds max wait
                    await asyncio.sleep(0.1)
                    cached_val = RedisCacheService.get_value(cache_key)
                    if cached_val is not None:
                        return cached_val
                
                # Timeout occurred -> fallback to execution
                CACHE_METRICS["lock_timeouts"] += 1
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            repr_args = [_get_serializable_repr(a) for a in args]
            repr_kwargs = {k: _get_serializable_repr(v) for k, v in kwargs.items()}
            arg_str = str(repr_args) + str(sorted(repr_kwargs.items()))
            cache_key = f"cache:{namespace}:{hash(arg_str)}"
            
            cached_val = RedisCacheService.get_value(cache_key)
            if cached_val is not None:
                return cached_val

            lock_key = f"lock:{cache_key}"
            lock_acquired = redis_client.set(lock_key, "locked", ex=10, nx=True)

            if lock_acquired:
                try:
                    result = func(*args, **kwargs)
                    RedisCacheService.set_value(cache_key, result, ttl=ttl, tags=tags)
                    return result
                finally:
                    redis_client.delete(lock_key)
            else:
                CACHE_METRICS["lock_waits"] += 1
                for _ in range(30):
                    time.sleep(0.1)
                    cached_val = RedisCacheService.get_value(cache_key)
                    if cached_val is not None:
                        return cached_val
                
                CACHE_METRICS["lock_timeouts"] += 1
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
