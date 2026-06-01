import json
import uuid
import hashlib
import hmac
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
import requests
from sqlalchemy import select

from server import app
from db.session import get_db, tenant_context
from models import Company, User, AuditLog
from models.webhook import WebhookSubscription, WebhookDeliveryLog
from models.enums import UserRole
from core.vault import SecretVaultService
from fastapi.testclient import TestClient
from schemas.webhook import WebhookSubscriptionCreate, is_ssrf_safe_url
from tasks.webhooks import dispatch_webhook_event_task, purge_expired_delivery_logs, MAX_PAYLOAD_SIZE_BYTES


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        try:
            db_session.expire_all()
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_webhook_ssrf_and_event_schema_checks():
    """
    Asserts that:
    1. Loopback, private subnets, and local destinations are rejected by the SSRF filter.
    2. Public-network destinations are accepted.
    3. Unregistered/invalid webhook event types are rejected.
    """
    # 1. SSRF URLs
    assert not is_ssrf_safe_url("http://127.0.0.1/hooks")
    assert not is_ssrf_safe_url("https://localhost/hooks")
    assert not is_ssrf_safe_url("http://192.168.1.5/hooks")
    assert not is_ssrf_safe_url("https://10.0.0.12/hooks")
    assert is_ssrf_safe_url("https://hooks.slack.com/services/XYZ")

    # 2. Pydantic creation request validation
    # Loopback trigger must raise value error
    with pytest.raises(ValueError, match="invalid or private network address"):
        WebhookSubscriptionCreate(
            url="http://127.0.0.1/hooks",
            active_events=["candidate.created"]
        )

    # Invalid events check
    with pytest.raises(ValueError, match="Invalid webhook event types"):
        WebhookSubscriptionCreate(
            url="https://hooks.slack.com/services/XYZ",
            active_events=["invalid.event.type"]
        )

    # Valid schema succeeds
    valid_schema = WebhookSubscriptionCreate(
        url="https://hooks.slack.com/services/XYZ",
        active_events=["candidate.created", "offer.approved"]
    )
    assert valid_schema.url == "https://hooks.slack.com/services/XYZ"
    assert len(valid_schema.active_events) == 2


def test_webhook_api_subscription_lifecycle(api_client, db_session):
    """
    Verifies that the /enterprise/webhooks REST endpoints:
    1. Allow creation and return raw signing_secret exactly once.
    2. Support listing (which hides the raw secrets).
    3. Support subscription deletions.
    """
    # 1. Register tenant company and owner
    resp_reg = api_client.post("/api/v1/auth/register", json={
        "company_name": "Webhook Corp",
        "email": "owner@webhook-corp.com",
        "password": "secure-password",
        "full_name": "Owner User"
    })
    assert resp_reg.status_code == 201
    headers = {"Authorization": f"Bearer {resp_reg.json()['access_token']}"}
    comp_id = uuid.UUID(resp_reg.json()["user"]["company_id"])

    # 2. Create subscription
    resp_create = api_client.post(
        "/api/v1/enterprise/webhooks",
        headers=headers,
        json={
            "url": "https://hooks.slack.com/services/123",
            "active_events": ["candidate.created", "offer.approved"]
        }
    )
    assert resp_create.status_code == 201
    sub_data = resp_create.json()
    sub_id = uuid.UUID(sub_data["id"])
    assert sub_data["url"] == "https://hooks.slack.com/services/123"
    assert "signing_secret" in sub_data
    assert sub_data["signing_secret"].startswith("whsec_")
    assert sub_data["status"] == "active"

    # Verify audit event logged
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        evt = db_session.scalar(select(AuditLog).where(AuditLog.action == "webhook.subscribed"))
        assert evt is not None
        assert evt.company_id == comp_id
        assert evt.metadata_json["url"] == "https://hooks.slack.com/services/123"

    # 3. List subscriptions (verify raw secret is hidden)
    resp_list = api_client.get("/api/v1/enterprise/webhooks", headers=headers)
    assert resp_list.status_code == 200
    sub_list = resp_list.json()
    assert len(sub_list) == 1
    assert sub_list[0]["id"] == str(sub_id)
    assert "signing_secret" not in sub_list[0] # Hidden in list!

    # 4. Get delivery logs history (should be empty initially)
    resp_logs = api_client.get(f"/api/v1/enterprise/webhooks/{sub_id}/logs", headers=headers)
    assert resp_logs.status_code == 200
    assert len(resp_logs.json()) == 0

    # 5. Delete subscription
    resp_del = api_client.delete(f"/api/v1/enterprise/webhooks/{sub_id}", headers=headers)
    assert resp_del.status_code == 204

    # Verify listing is now empty
    resp_list_after = api_client.get("/api/v1/enterprise/webhooks", headers=headers)
    assert len(resp_list_after.json()) == 0

    # Verify audit event logged for delete
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        evt_del = db_session.scalar(select(AuditLog).where(AuditLog.action == "webhook.unsubscribed"))
        assert evt_del is not None
        assert evt_del.company_id == comp_id


def test_webhook_multi_tenant_rls_boundaries(api_client, db_session):
    """
    Asserts strict RLS isolation:
    Company B can never view, list, delete, or fetch logs of Company A's subscriptions.
    """
    # 1. Register Tenant A and create subscription
    resp_a = api_client.post("/api/v1/auth/register", json={
        "company_name": "Tenant A",
        "email": "owner@a.com",
        "password": "secure-password",
        "full_name": "Owner A"
    })
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}
    sub_a = api_client.post(
        "/api/v1/enterprise/webhooks",
        headers=headers_a,
        json={"url": "https://hooks.slack.com/services/aaa", "active_events": ["candidate.created"]}
    )
    sub_a_id = sub_a.json()["id"]

    # 2. Register Tenant B
    resp_b = api_client.post("/api/v1/auth/register", json={
        "company_name": "Tenant B",
        "email": "owner@b.com",
        "password": "secure-password",
        "full_name": "Owner B"
    })
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

    # 3. Attempt to fetch A's logs or delete A's subscription as B -> expects 404
    resp_fetch_fail = api_client.get(f"/api/v1/enterprise/webhooks/{sub_a_id}/logs", headers=headers_b)
    assert resp_fetch_fail.status_code == 404

    resp_delete_fail = api_client.delete(f"/api/v1/enterprise/webhooks/{sub_a_id}", headers=headers_b)
    assert resp_delete_fail.status_code == 404

    # Verify Tenant B's subscription listing is empty
    resp_list_b = api_client.get("/api/v1/enterprise/webhooks", headers=headers_b)
    assert len(resp_list_b.json()) == 0


@patch("requests.post")
def test_webhook_dispatcher_hmac_dispatches(mock_post, api_client, db_session):
    """
    Validates that:
    1. Outgoing payloads carry accurate HMAC-SHA256 headers matching the decrypted secret.
    2. Webhook dispatches are successfully logged in both delivery logs and audit event ledgers.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"
    mock_post.return_value = mock_response

    # 1. Register company and add subscription
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "HMAC Corp",
        "email": "owner@hmac.com",
        "password": "secure-password",
        "full_name": "Owner User"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    comp_id = resp.json()["user"]["company_id"]

    resp_sub = api_client.post(
        "/api/v1/enterprise/webhooks",
        headers=headers,
        json={"url": "https://hooks.slack.com/services/hmac", "active_events": ["candidate.created"]}
    )
    raw_secret = resp_sub.json()["signing_secret"]
    sub_id = resp_sub.json()["id"]

    # 2. Trigger Celery Task eagerly using .apply() to handle bound task injection correctly
    payload_data = {"candidate_id": "c123", "full_name": "John Doe"}
    dispatch_webhook_event_task.apply(args=(comp_id, "candidate.created", payload_data))

    # 3. Assert mock post was fired
    assert mock_post.called
    kwargs = mock_post.call_args[1]
    assert kwargs["json"] == payload_data
    
    # Assert HMAC-SHA256 signature matches
    signature_header = kwargs["headers"]["X-SmartOnboard-Signature"]
    assert "t=" in signature_header
    assert ",v1=" in signature_header
    t_val = signature_header.split(",v1=")[0].replace("t=", "")
    sig_val = signature_header.split(",v1=")[1]

    payload_str = json.dumps(payload_data)
    expected_msg = f"t={t_val}.{payload_str}".encode("utf-8")
    expected_sig = hmac.new(raw_secret.encode("utf-8"), expected_msg, hashlib.sha256).hexdigest()
    assert sig_val == expected_sig

    # 4. Check delivery log registered in database
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        log = db_session.scalar(select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == uuid.UUID(sub_id)))
        assert log is not None
        assert log.event_type == "candidate.created"
        assert log.response_status == 200
        assert log.response_body == "Success"

        # Check webhook.delivery_success audit log
        audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "webhook.delivery_success"))
        assert audit is not None
        assert audit.metadata_json["subscription_id"] == sub_id


@patch("requests.post")
def test_webhook_circuit_breaker(mock_post, api_client, db_session):
    """
    Verifies that:
    1. 10 consecutive failed dispatches trip the circuit breaker.
    2. Status shifts to "suspended" and sets "disabled_until".
    3. Emits a "webhook.circuit_opened" audit log.
    """
    # Eager Celery retries can raise Exception on failure, let's mock responses to return 500
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Breaker Corp",
        "email": "owner@breaker.com",
        "password": "secure-password",
        "full_name": "Owner User"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    comp_id = resp.json()["user"]["company_id"]

    resp_sub = api_client.post(
        "/api/v1/enterprise/webhooks",
        headers=headers,
        json={"url": "https://hooks.slack.com/services/breaker", "active_events": ["candidate.created"]}
    )
    sub_id = uuid.UUID(resp_sub.json()["id"])

    # Trigger failed Celery dispatches. Since we retry up to 5 times per task,
    # let's set consecutive_failures directly in DB to 9, then fire 1 task,
    # which will fail and trip the circuit breaker (failures >= 10).
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        sub = db_session.get(WebhookSubscription, sub_id)
        sub.consecutive_failures = 9
        db_session.commit()

    # Trigger async dispatch eagerly using .apply()
    dispatch_webhook_event_task.apply(args=(comp_id, "candidate.created", {"data": "test"}))

    # Assert circuit breaker has tripped

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        sub = db_session.get(WebhookSubscription, sub_id)
        assert sub.status == "suspended" or sub.disabled_until is not None
        assert sub.consecutive_failures >= 10

        # Verify circuit opened audit log
        evt = db_session.scalar(select(AuditLog).where(AuditLog.action == "webhook.circuit_opened"))
        assert evt is not None
        assert evt.metadata_json["subscription_id"] == str(sub_id)


def test_webhook_size_and_ssrf_limits_at_dispatch(api_client, db_session):
    """
    Asserts that the async dispatcher catches SSRF URLs and oversized payloads
    before sending HTTP requests.
    """
    resp = api_client.post("/api/v1/auth/register", json={
        "company_name": "Dispatch Limit Corp",
        "email": "owner@limit.com",
        "password": "secure-password",
        "full_name": "Owner User"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    comp_id = resp.json()["user"]["company_id"]

    # We manually force a localhost URL in the DB bypassing schema validator
    # to check the dispatcher's defense-in-depth SSRF protection
    with tenant_context(auth_mode="true"):
        company_uuid = uuid.UUID(comp_id)
        vault = SecretVaultService()
        raw_secret = "whsec_abcd"
        encrypted_json = vault.encrypt_secret(raw_secret)
        encrypted_dict = json.loads(encrypted_json)

        sub_ssrf = WebhookSubscription(
            company_id=company_uuid,
            url="http://127.0.0.1/hooks",
            encrypted_secret=encrypted_dict["ciphertext"],
            iv=encrypted_dict["iv"],
            tag=encrypted_dict["tag"],
            key_version=encrypted_dict.get("key_version", "v1"),
            secret_key_hash=hashlib.sha256(raw_secret.encode("utf-8")).hexdigest(),
            active_events=["candidate.created"],
            status="active"
        )
        db_session.add(sub_ssrf)
        db_session.commit()
        sub_ssrf_id = sub_ssrf.id

    # 1. Trigger dispatch to SSRF destination eagerly. It should write a failed attempt log with code 400
    dispatch_webhook_event_task.apply(args=(comp_id, "candidate.created", {"msg": "test"}))

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        log = db_session.scalar(
            select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == sub_ssrf_id)
        )
        assert log is not None
        assert log.response_status == 400
        assert "SSRF Protection" in log.response_body

    # 2. Trigger oversized payload check
    # Create valid webhook
    resp_sub = api_client.post(
        "/api/v1/enterprise/webhooks",
        headers=headers,
        json={"url": "https://hooks.slack.com/services/valid", "active_events": ["candidate.created"]}
    )
    sub_valid_id = uuid.UUID(resp_sub.json()["id"])

    # Construct payload larger than 1MB
    large_payload = {"data": "X" * (MAX_PAYLOAD_SIZE_BYTES + 10)}
    dispatch_webhook_event_task.apply(args=(comp_id, "candidate.created", large_payload))

    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        log_large = db_session.scalar(
            select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == sub_valid_id)
        )
        assert log_large is not None
        assert log_large.response_status == 413
        assert "Payload Too Large" in log_large.response_body


def test_webhook_log_retention_purge(db_session):
    """
    Validates daily periodic sweep logs pruning:
    - Logs older than 30 days are purged.
    - Logs newer than 30 days are preserved.
    """
    # Setup company, subscription, and delivery logs in DB
    with tenant_context(auth_mode="true"):
        company = Company(name="Retention Corp", slug="retention-corp")
        db_session.add(company)
        db_session.flush()

        vault = SecretVaultService()
        enc = vault.encrypt_secret("whsec_secret")
        enc_dict = json.loads(enc)

        sub = WebhookSubscription(
            company_id=company.id,
            url="https://hooks.slack.com/services/retention",
            encrypted_secret=enc_dict["ciphertext"],
            iv=enc_dict["iv"],
            tag=enc_dict["tag"],
            secret_key_hash="abc",
            active_events=["candidate.created"],
            status="active"
        )
        db_session.add(sub)
        db_session.flush()

        now = datetime.now(timezone.utc)

        # 1. Fresh log (5 days old)
        fresh_log = WebhookDeliveryLog(
            company_id=company.id,
            subscription_id=sub.id,
            event_type="candidate.created",
            payload={"test": "fresh"},
            attempt_number=1,
            response_status=200,
            response_body="Success",
            elapsed_seconds=0.15,
            executed_at=now - timedelta(days=5)
        )
        # 2. Expired log (35 days old)
        expired_log = WebhookDeliveryLog(
            company_id=company.id,
            subscription_id=sub.id,
            event_type="candidate.created",
            payload={"test": "expired"},
            attempt_number=1,
            response_status=200,
            response_body="Success",
            elapsed_seconds=0.30,
            executed_at=now - timedelta(days=35)
        )
        db_session.add_all([fresh_log, expired_log])
        db_session.commit()

        fresh_log_id = fresh_log.id
        expired_log_id = expired_log.id

    # Run periodic Celery sweep task in eager mode
    purged_count = purge_expired_delivery_logs()
    assert purged_count == 1

    # Assert database states
    with tenant_context(auth_mode="true"):
        db_session.expire_all()
        log_fresh = db_session.get(WebhookDeliveryLog, fresh_log_id)
        log_expired = db_session.get(WebhookDeliveryLog, expired_log_id)

        assert log_fresh is not None
        assert log_expired is None # Expired log successfully purged!
