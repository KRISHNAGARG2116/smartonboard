import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from core.celery_app import celery_app
from core.vault import SecretVaultService
from core.smtp import verify_smtp_credentials
from core.audit import log_audit_event
from db.session import tenant_context, SessionLocal
from models.enterprise import CompanySMTPSettings

logger = logging.getLogger("celery")


@celery_app.task
def reverify_all_smtp_settings_task():
    """
    Sweeps all custom SMTP configurations in the database.
    If the last verification was more than 90 days ago, it runs the SMTP STARTTLS / SSL handshake
    to automatically refresh/re-verify the connection.
    """
    # Use global bypass context to query across all tenants
    with tenant_context(auth_mode="true"):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            expiry_threshold = now - timedelta(days=90)

            # Find all SMTP settings that were verified but have now passed the 90-day threshold
            stmt = select(CompanySMTPSettings).where(
                CompanySMTPSettings.verification_status == "verified",
                CompanySMTPSettings.last_verified_at < expiry_threshold
            )
            settings_to_reverify = db.scalars(stmt).all()

            logger.info(f"SMTP Sweep: Found {len(settings_to_reverify)} company SMTP settings requiring re-verification.")

            for smtp_setting in settings_to_reverify:
                # Retrieve and decrypt custom password
                try:
                    vault = SecretVaultService()
                    envelope = {
                        "ciphertext": smtp_setting.encrypted_password,
                        "iv": smtp_setting.iv,
                        "tag": smtp_setting.tag,
                        "key_version": smtp_setting.key_version
                    }
                    password_plain = vault.decrypt_secret(json.dumps(envelope))

                    # Perform credentials connection test
                    verify_smtp_credentials(
                        hostname=smtp_setting.hostname,
                        port=smtp_setting.port,
                        username=smtp_setting.username,
                        password_plain=password_plain
                    )

                    # Success: Refresh verification state
                    smtp_setting.verification_status = "verified"
                    smtp_setting.last_verified_at = now
                    smtp_setting.last_verification_error = None
                    db.add(smtp_setting)
                    db.flush()

                    # Log enterprise.smtp_reverified compliance audit event
                    log_audit_event(
                        db=db,
                        action="enterprise.smtp_reverified",
                        actor_type="SYSTEM",
                        company_id=smtp_setting.company_id,
                        resource_type="company_smtp_settings",
                        resource_id=str(smtp_setting.id),
                        metadata={
                            "smtp_setting_id": str(smtp_setting.id),
                            "hostname": smtp_setting.hostname,
                            "port": smtp_setting.port,
                        }
                    )
                    logger.info(f"Successfully re-verified SMTP settings for company {smtp_setting.company_id}.")

                except Exception as exc:
                    # Failure: demote status to failed, write error log
                    smtp_setting.verification_status = "failed"
                    smtp_setting.last_verification_error = str(exc)
                    db.add(smtp_setting)
                    db.flush()

                    # Log enterprise.smtp_test_failed compliance audit event
                    log_audit_event(
                        db=db,
                        action="enterprise.smtp_test_failed",
                        actor_type="SYSTEM",
                        company_id=smtp_setting.company_id,
                        resource_type="company_smtp_settings",
                        resource_id=str(smtp_setting.id),
                        metadata={
                            "smtp_setting_id": str(smtp_setting.id),
                            "hostname": smtp_setting.hostname,
                            "port": smtp_setting.port,
                            "error": str(exc),
                        }
                    )
                    logger.warning(f"SMTP re-verification failed for company {smtp_setting.company_id}: {str(exc)}")

            db.commit()
            return len(settings_to_reverify)

        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to execute SMTP settings re-verification sweep: {exc}")
            raise exc
        finally:
            db.close()
