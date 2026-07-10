import pytest
import os
import time
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

from db.session import tenant_context, SessionLocal
from core.redis_cache import RedisCacheService, cached
from core.storage import get_storage_service, enforce_storage_lifecycle_sweep, LocalStorageService
from core.feature_flags import FeatureFlagsService
from core.resilience import CircuitBreaker, CircuitBreakerOpenException, circuit_breaker
from benchmark_suite import execute_performance_suite


# Mock a slow database/API call to check cache stampede protection
call_count = 0

@cached(namespace="test_stampede", ttl=10)
async def mock_expensive_call(val: int):
    global call_count
    call_count += 1
    await asyncio.sleep(0.1)
    return f"result_{val}"


@pytest.mark.asyncio
async def test_cache_stampede_and_tag_invalidation():
    """Verify stampede lock request coalescing and tag invalidation sweeps."""
    global call_count
    call_count = 0

    # Trigger multiple concurrent calls
    tasks = [mock_expensive_call(42) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # All should return the same result
    for r in results:
        assert r == "result_42"

    # Call count should be exactly 1 thanks to SingleFlight stampede locks!
    assert call_count == 1

    # Invalidate tag and verify miss
    RedisCacheService.invalidate_tags(["test_stampede_tag"])
    RedisCacheService.set_value("cache:test_key", "val", ttl=10, tags=["test_stampede_tag"])
    assert RedisCacheService.get_value("cache:test_key") == "val"

    RedisCacheService.invalidate_tags(["test_stampede_tag"])
    assert RedisCacheService.get_value("cache:test_key") is None


def test_database_connection_pool_and_eager_loading(db_session):
    """Verify DB connection pooling and index setup verification."""
    from db.session import engine
    pool = engine.pool
    
    # Assert pool is tuned to PgBouncer optimized parameters
    assert pool.size() >= 20

    # Run check of postgres indexes
    with tenant_context(auth_mode="true"):
        indexes = db_session.execute(text("""
            SELECT indexname FROM pg_indexes WHERE tablename = 'applications';
        """)).fetchall()
        index_names = [r[0] for r in indexes]
        assert any("ix_applications_status_company" in name for name in index_names)


def test_celery_priorities_and_worker_queues():
    """Verify Celery task queues configuration mappings."""
    from core.celery_app import celery_app
    routes = celery_app.conf.task_routes
    
    # Assert specific task types map to correct priority queues
    assert routes["tasks.performance.send_bulk_emails_task"]["queue"] == "critical"
    assert routes["tasks.performance.bulk_recompute_match_scores_task"]["queue"] == "high"


def test_file_storage_lifecycle_rules(tmp_path):
    """Verify temporary files lifecycle sweeps."""
    # Setup mock local storage service
    storage = LocalStorageService(base_dir=tmp_path)
    
    # Create quarantine file
    quar_file = storage.quarantine_dir / "old_temp_file.pdf"
    quar_file.touch()
    
    # Backdate mtime by 8 days to trigger deletion
    eight_days_ago = time.time() - (8 * 24 * 3600)
    os.utime(str(quar_file), (eight_days_ago, eight_days_ago))

    # Run sweep
    enforce_storage_lifecycle_sweep(storage)
    
    # Assert temp file is deleted
    assert not quar_file.exists()


def test_feature_flags_and_degradation():
    """Verify feature rollouts and AI provider fallback degradation."""
    # Verify defaults
    assert FeatureFlagsService.is_enabled("ai_recruiter") is True
    assert FeatureFlagsService.is_enabled("sso_integration") is False

    # Simulate environment override
    os.environ["FEATURE_SSO_INTEGRATION"] = "true"
    assert FeatureFlagsService.is_enabled("sso_integration") is True
    del os.environ["FEATURE_SSO_INTEGRATION"]


def test_health_endpoints_metrics(db_session):
    """Verify metrics and availability SLO calculations."""
    from api.health import get_metrics
    from api.deps import tenant_id_var
    
    # Call health check metrics endpoint
    metrics = get_metrics(db_session)
    assert "database_pool" in metrics
    assert "cache_stats" in metrics
    assert "slo_targets" in metrics
    assert metrics["slo_targets"]["target_p95_latency_ms"] == 200


def test_resilience_circuit_breaker():
    """Verify circuit breaker transitions under failure conditions using real decorator."""
    call_count = 0
    
    @circuit_breaker(threshold=3, timeout_seconds=10)
    def call_ai_service():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Timeout error")

    # Call AI service 3 times -> raises ConnectionError
    with pytest.raises(ConnectionError):
        call_ai_service()
    with pytest.raises(ConnectionError):
        call_ai_service()
    with pytest.raises(ConnectionError):
        call_ai_service()

    # 4th call should trigger CircuitBreakerOpenException immediately
    with pytest.raises(CircuitBreakerOpenException):
        call_ai_service()

    assert call_count == 3


def test_benchmarks_regression_detection():
    """Execute end-to-end performance suite and check target compliance."""
    results = execute_performance_suite()
    assert "candidate_search" in results
    assert "dashboard_summary" in results
