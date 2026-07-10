import time
import random
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitBreakerOpenException(Exception):
    """Raised when the circuit breaker is open and blocks executions."""
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failures = 0
        self.last_failure_time = 0.0

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit Breaker transitioned to OPEN state (failures={self.failures})")

    def allow_execution(self) -> bool:
        if self.state == "OPEN":
            # Check recovery timeout
            if time.time() - self.last_failure_time > self.recovery_timeout_seconds:
                self.state = "HALF-OPEN"
                logger.warning("Circuit Breaker transitioned to HALF-OPEN state for testing recovery")
                return True
            return False
        return True


def circuit_breaker(threshold: int = 3, timeout_seconds: int = 30):
    """
    Decorator to wrap third-party API calls with a Circuit Breaker pattern.
    """
    cb = CircuitBreaker(failure_threshold=threshold, recovery_timeout_seconds=timeout_seconds)

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cb.allow_execution():
                raise CircuitBreakerOpenException("Circuit Breaker is OPEN: request rejected.")
            try:
                result = func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise e
        return wrapper
    return decorator


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """
    Decorator for retrying transient failures with exponential backoff and jitter.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # Calculate delay with jitter
                    sleep_time = min(max_delay, delay * (2 ** attempt)) + random.uniform(0, 0.5)
                    logger.warning(f"Transient error: {e}. Retrying in {sleep_time:.2f}s (Attempt {attempt+1}/{max_retries})")
                    time.sleep(sleep_time)
                    
            raise last_exception
        return wrapper
    return decorator
